"""Seed the fictional on-ramp in an existing staff account; never creates credentials."""
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import User
from cloudfiles.providers.drive_snapshot import DriveSnapshotProvider
from datarooms.models import Dataroom
from dealroom.drive import import_tree, match_template, room_state, save_state, walk_tree
from dealroom.models import RoomPolicy
from dealroom.onramp import personal_url
from dealroom.activity import record
from dealroom_sign.models import NdaPolicy
from dealroom_sign import nda_template
from dealroom.uploads import upload
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
        email = options['visitor'].strip().lower()
        nodes = walk_tree(provider, options['folder_id'])
        room, _ = Dataroom.objects.get_or_create(organization=user.organization, name='Harbor Light Analytics · Series A',
                                               defaults={'created_by': user, 'enable_qna': False})
        if room.created_by_id != user.pk:
            raise CommandError('This demo room belongs to another owner.')
        link, _ = ShareLink.objects.get_or_create(dataroom=room, name='Room entry', defaults={
            'created_by': user, 'restrict_to_grants': True, 'requires_email': True,
            'requires_email_verification': True, 'enable_watermark': True, 'enable_qna': False})
        RoomPolicy.objects.get_or_create(room=room, defaults={'entry_link': link})
        matches = match_template(nodes)
        choices = {f['id']: f['slot'] for f in matches['matched']}
        import_tree(room, user, {options['folder_id']: provider}, nodes, '' if options['keep_folders'] else 'series_a', choices)
        state = room_state(room)
        state['note'] = 'Thanks for taking a look. Start with the model, then the deck. I’m around this week to walk through it. — Dan'
        state['start_here'] = [state['slots'][s] for s in ('model', 'deck') if s in state['slots']]
        state['require_nda'] = True
        save_state(room, user, state)
        fixture = Path(__file__).resolve().parents[2] / 'tests/fixtures/Investor NDA (fictional).pdf'
        pdf = fixture.read_bytes()
        policy = NdaPolicy.objects.filter(room=room).first()
        if not policy or policy.source_sha256 != nda_template.digest(pdf):
            version = upload(room, user, SimpleUploadedFile(fixture.name, pdf, content_type='application/pdf'), entry_nda=True)
            policy = nda_template.save_policy(room, user, version, pdf)
        if not policy.enabled:
            policy = nda_template.save_policy(room, user, policy.source_version, pdf)
        if not nda_template.confirmed(policy):
            fields = nda_template.suggestions(pdf)
            if not fields:
                raise CommandError('Place the NDA fields: no blank recipient signature rule was found.')
            policy = nda_template.save_policy(room, user, policy.source_version, pdf, fields=fields,
                confirm=True, revision=str(policy.revision))
        for page in sorted({f['page'] for f in policy.fields}):
            count = sum(f['page'] == page for f in policy.fields)
            self.stdout.write(f'confirmed {count} fields on page {page}')
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
