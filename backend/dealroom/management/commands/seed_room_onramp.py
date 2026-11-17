"""Seed the fictional on-ramp in an existing staff account; never creates credentials."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import User
from cloudfiles.providers.drive_snapshot import DriveSnapshotProvider
from datarooms.models import Dataroom
from dealroom.drive import import_tree, match_template, room_state, save_state, walk_tree
from dealroom.models import RoomPolicy
from dealroom.onramp import personal_url
from dealroom.activity import record
from dealroom_sign.models import NdaPolicy
from sharelinks.models import ShareLink, ShareLinkAccessGrant, Viewer, ViewerOrganisation


class Command(BaseCommand):
    help = 'Seed the fictional Harbor Light room from a snapshot, with a personal demo link (no email sent).'

    def add_arguments(self, parser):
        parser.add_argument('--owner', required=True, help='Existing staff email')
        parser.add_argument('--folder-id', default='harbor-light')
        parser.add_argument('--visitor', default='maya@northwind.test')
        parser.add_argument('--keep-folders', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        user = User.objects.filter(email=options['owner'], is_staff=True).first()
        if not user:
            raise CommandError('An existing staff owner is required.')
        provider = DriveSnapshotProvider(options['folder_id'])
        room, _ = Dataroom.objects.get_or_create(organization=user.organization, name='Harbor Light Analytics · Series A',
                                               defaults={'created_by': user, 'enable_qna': False})
        if room.created_by_id != user.pk:
            raise CommandError('This demo room belongs to another owner.')
        link, _ = ShareLink.objects.get_or_create(dataroom=room, name='Room entry', defaults={
            'created_by': user, 'restrict_to_grants': True, 'requires_email': True,
            'requires_email_verification': True, 'enable_watermark': True, 'enable_qna': False})
        RoomPolicy.objects.get_or_create(room=room, defaults={'entry_link': link})
        nodes = walk_tree(provider, options['folder_id'])
        matches = match_template(nodes)
        choices = {f['id']: f['slot'] for f in matches['matched']}
        import_tree(room, user, {options['folder_id']: provider}, nodes, '' if options['keep_folders'] else 'series_a', choices)
        state = room_state(room)
        state['note'] = 'Thanks for taking a look. Start with the model, then the deck. I’m around this week to walk through it. — Dan'
        state['start_here'] = [state['slots'][s] for s in ('model', 'deck') if s in state['slots']]
        state['require_nda'] = True
        save_state(room, user, state)
        nda_item = room.documents.filter(document__name__icontains='Mutual NDA').first()
        if nda_item:
            version = nda_item.document.versions.get(is_primary=True)
            NdaPolicy.objects.get_or_create(room=room, defaults={'source_version': version,
                'source_sha256': version.metadata['source_sha256'], 'enabled': True,
                'fields': [{'type': 'SIGNATURE', 'page': version.num_pages or 2, 'positionX': 10, 'positionY': 70, 'width': 30, 'height': 10}]})
        email = options['visitor'].strip().lower()
        firm, _ = ViewerOrganisation.objects.get_or_create(organization=user.organization, name='Northwind Ventures',
            defaults={'email_domains': [], 'created_by': user})
        Viewer.objects.get_or_create(organization=user.organization, email=email,
                                    defaults={'name': 'Maya Chen', 'recipient_org': firm})
        grant, _ = ShareLinkAccessGrant.objects.get_or_create(share_link=link, email=email, revoked_at=None,
                                                            defaults={'created_by': user, 'download_ceiling': 'none'})
        record('room.invited', organization=user.organization, actor=user, room_id=room.pk, target_id=grant.pk,
               data={'email': email, 'firm': email.rsplit('@', 1)[1], 'note': state['note']})
        self.stdout.write(f'Sender: /datarooms/{room.pk}')
        self.stdout.write(f'Visitor: {personal_url(room, grant)}')
        self.stdout.write('NDA remains enforced. Configure this owner’s existing Sign credentials before the visitor demo.')
