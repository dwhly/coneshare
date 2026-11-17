"""Prototype orchestration over existing room, grant, version and activity records."""
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from cloudfiles.providers.base import CloudProviderError
from cloudfiles.providers.drive_snapshot import DriveSnapshotProvider
from dealroom_sign.fleet_mail import send_mail
from dealroom_sign.models import NdaPolicy
from sharelinks.models import ShareLinkAccessGrant, Viewer, ViewerOrganisation
from .activity import record
from .brand import load_brand
from .domains import guarded_domain
from .drive import (SERIES_A, SLOTS, room_state, save_state, ensure_template, review,
                    import_tree, check_updates, publish_update)
from .models import Activity


def provider_error(fn):
    try:
        return fn()
    except CloudProviderError as exc:
        raise ValidationError(str(exc)) from exc


def firm_key(email):
    domain = email.rsplit('@', 1)[1]
    try:
        guarded_domain(domain)
        return domain
    except ValidationError:
        return email


def personal_url(room, grant, sender=None):
    token = signing.dumps({'room': str(room.pk), 'grant': str(grant.pk), 'email': grant.email,
                          'sender_name': getattr(sender or grant.created_by, 'name', '')}, salt='room-personal')
    return f'/view/{room.roompolicy.entry_link.slug}#personal={token}'


def pending_requests(room):
    events = Activity.objects.filter(room_id=str(room.pk), organization=room.organization)
    answered = set(events.filter(event_type='room.request_answered').values_list('target_id', flat=True))
    return [{'id': str(e.pk), **e.data, 'created_at': e.created_at} for e in events.filter(event_type='room.request') if str(e.pk) not in answered]


class RoomOnrampMixin:
    @extend_schema(request=dict, responses=dict)
    @action(detail=True, methods=['get', 'patch'])
    def outline(self, request, pk=None):
        room = self.get_object()
        if request.method == 'PATCH':
            type(room).objects.select_for_update().get(pk=room.pk)
        state = room_state(room)
        if request.method == 'PATCH':
            allowed = {'template', 'note', 'start_here', 'slots', 'not_needed', 'require_nda'}
            if set(request.data) - allowed:
                raise ValidationError('Unknown outline fields.')
            if request.data.get('template') == 'series_a':
                ensure_template(room, request.user, state)
                state.setdefault('require_nda', True)
            if 'note' in request.data:
                state['note'] = serializers.CharField(max_length=3000, allow_blank=True).run_validation(request.data['note'])
            ids = {str(i) for i in room.documents.values_list('pk', flat=True)}
            if 'start_here' in request.data:
                selected = request.data['start_here']
                if not isinstance(selected, list) or len(selected) > 6 or any(i not in ids for i in selected):
                    raise ValidationError('Choose up to six room documents.')
                state['start_here'] = list(dict.fromkeys(selected))
            if 'slots' in request.data:
                slots = request.data['slots']
                if not isinstance(slots, dict) or any(k not in SLOTS or v not in ids for k, v in slots.items()) or len(set(slots.values())) != len(slots):
                    raise ValidationError('Choose one room document per valid slot.')
                folders = ensure_template(room, request.user, state)
                for slot, item_id in slots.items():
                    room.documents.filter(pk=item_id).update(folder=folders[SLOTS[slot]['folder']])
                state['slots'] = slots
            if 'not_needed' in request.data:
                values = request.data['not_needed']
                if not isinstance(values, list) or any(k not in SLOTS for k in values):
                    raise ValidationError('Choose valid slots.')
                state['not_needed'] = values
            if 'require_nda' in request.data:
                state['require_nda'] = serializers.BooleanField().run_validation(request.data['require_nda'])
                # Existing Sign policies remain authoritative, even if this preference is off.
            save_state(room, request.user, state)
        documents = []
        for item in room.documents.select_related('document', 'folder').all():
            version = item.document.versions.filter(is_primary=True).first()
            documents.append({'id': str(item.pk), 'name': item.name or item.document.name,
                'document_id': str(item.document_id), 'folder_id': str(item.folder_id or ''),
                'version_id': str(version.pk) if version else '', 'page_count': version.num_pages if version else 0,
                'source': version.metadata.get('drive_source') if version else None})
        invites = Activity.objects.filter(room_id=str(room.pk), organization=room.organization, event_type='room.invited')
        pending = pending_requests(room)
        checked = Activity.objects.filter(room_id=str(room.pk), organization=room.organization,
                                          event_type='room.drive_checked').first()
        present_ids = {doc['id'] for doc in documents}
        state['slots'] = {slot: id for slot, id in state['slots'].items() if id in present_ids}
        missing = [slot for slot in SLOTS.values() if slot['id'] not in state['slots']
                   and slot['id'] not in state['not_needed']]
        return Response({**state, 'groups': SERIES_A, 'slot_definitions': SLOTS, 'documents': documents,
            'missing_slots': missing if state['template'] else [],
            'needs_you': pending, 'needs_you_count': len(pending), 'invitations': [e.data for e in invites],
            'drive_checked_at': checked.created_at.isoformat() if checked else None,
            'nda_configured': NdaPolicy.objects.filter(room=room, enabled=True).exists(),
            'policy': {'status': room.roompolicy.status, 'expires_at': room.roompolicy.expires_at},
            'drive_enabled': bool(settings.DEALROOM_DRIVE_SNAPSHOT_DIR)})

    @extend_schema(request=dict, responses=dict)
    @action(detail=True, methods=['post'], url_path='drive-review')
    def drive_review(self, request, pk=None):
        room = self.get_object()
        existing_ids = {version.metadata.get('drive_source', {}).get('id')
                        for item in room.documents.select_related('document')
                        for version in item.document.versions.filter(is_primary=True)}
        result = provider_error(lambda: review(request.data.get('links'), request.data.get('template', ''), existing_ids))
        # Bind this review to the tenant room; the signed tree cannot be edited by the browser.
        result['ticket'] = signing.dumps({'room': str(room.pk), 'review': result['ticket']}, salt='room-drive', compress=True)
        return Response(result)

    @extend_schema(request=dict, responses=dict)
    @action(detail=True, methods=['post'], url_path='drive-import')
    def drive_import(self, request, pk=None):
        room = self.get_object()
        try:
            ticket = signing.loads(request.data.get('ticket', ''), salt='room-drive', max_age=3600)
            if ticket['room'] != str(room.pk):
                raise ValueError('room')
            data = signing.loads(ticket['review'], salt='drive-review', max_age=3600)
        except (signing.BadSignature, ValueError, KeyError, TypeError) as exc:
            raise ValidationError('Review expired. Read the folders again.') from exc
        def run():
            providers = {r['id']: DriveSnapshotProvider(r['id']) for r in data['roots']}
            return import_tree(room, request.user, providers, data['nodes'], data['template'],
                               request.data.get('choices', {}), request.data.get('excluded', []),
                               request.data.get('destinations', {}))
        return Response({'imported': provider_error(run)}, status=201)

    @extend_schema(request=dict, responses=dict)
    @action(detail=True, methods=['get', 'post'], url_path='drive-updates')
    def drive_updates(self, request, pk=None):
        room = self.get_object()
        def run():
            providers = {root: DriveSnapshotProvider(root) for root in room_state(room)['drive_roots']}
            updates = check_updates(room, providers)
            if request.method == 'POST':
                selected = next((u for u in updates if u['item_id'] == request.data.get('item_id')), None)
                if not selected or selected['modifiedTime'] != request.data.get('modifiedTime'):
                    raise ValidationError('Update changed or already published. Check Drive again.')
                new = publish_update(room, request.user, providers[selected['root_id']], selected)
                return {'version_id': str(new.pk)}
            checked = record('room.drive_checked', organization=room.organization, actor=request.user, room_id=room.pk)
            return {'updates': updates, 'checked_at': checked.created_at.isoformat()}
        return Response(provider_error(run))

    @extend_schema(request=dict, responses=dict)
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        room = self.get_object()
        people = request.data.get('emails', [])
        notes = request.data.get('notes', {})
        if not isinstance(people, list) or not 1 <= len(people) <= 50 or not isinstance(notes, dict):
            raise ValidationError('Enter 1–50 email addresses and a note per firm.')
        emails = list(dict.fromkeys(serializers.EmailField().run_validation(e).lower() for e in people))
        invitations = []
        for email in emails:
            domain = email.rsplit('@', 1)[1]
            note = serializers.CharField(max_length=3000, allow_blank=True).run_validation(notes.get(domain, room_state(room)['note']))
            org, _ = ViewerOrganisation.objects.get_or_create(organization=room.organization, name=domain,
                defaults={'created_by': request.user, 'email_domains': []})
            Viewer.objects.get_or_create(organization=room.organization, email=email,
                defaults={'name': email.split('@')[0], 'recipient_org': org})
            grant = room.roompolicy.entry_link.access_grants.filter(email=email, revoked_at__isnull=True).first()
            if not grant:
                grant = ShareLinkAccessGrant.objects.create(share_link=room.roompolicy.entry_link, email=email,
                    created_by=request.user, download_ceiling='none')
            url = personal_url(room, grant, request.user)
            record('room.invited', organization=room.organization, actor=request.user, room_id=room.pk,
                   target_id=grant.pk, data={'email': email, 'firm': firm_key(email), 'note': note})
            brand = load_brand()
            body = f'{note}\n\n{room.name}\n{settings.SITE_DOMAIN.rstrip("/")}{url}\n\nYour personal link. No account needed. NDA in Sign; watermarked pages; downloads off. Link expires in 30 days.'
            transaction.on_commit(lambda email=email, body=body: send_mail(f'{room.name} · your room invitation', body, brand['email_sender'], [email]))
            invitations.append({'email': email, 'url': url})
        return Response({'invitations': invitations}, status=201)

    @extend_schema(request=dict, responses=dict)
    @action(detail=True, methods=['post'])
    def answer(self, request, pk=None):
        room = self.get_object()
        question = Activity.objects.filter(pk=request.data.get('id'), room_id=str(room.pk),
            organization=room.organization, event_type='room.request').first()
        if not question:
            raise ValidationError('Request not found.')
        text = serializers.CharField(max_length=5000).run_validation(request.data.get('text'))
        faq = serializers.BooleanField().run_validation(request.data.get('faq', False))
        record('room.request_answered', organization=room.organization, actor=request.user, room_id=room.pk,
            target_id=question.pk, data={'text': text, 'firm': question.data['firm'], 'faq': faq})
        return Response({'status': 'answered'})
