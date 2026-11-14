"""Operator-reviewed link import. No native mutation or legacy identity upgrade."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.models import User
from dealroom_sign.client import Documenso
from dealroom_sign.evidence import refresh_audit, snapshot_fields
from dealroom_sign.legacy import legacy_request
from dealroom_sign.models import BoardStaffBinding, Workflow
from dealroom_sign.requests import board_config
from dealroom_sign.workflows import validate_envelope


class Command(BaseCommand):
    help = 'Import reviewed board bindings/links; dry-run unless --apply. --fetch-audit is read-only and requires --apply to fetch.'

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True)
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--fetch-audit', action='store_true')

    def handle(self, *args, **options):
        try:
            manifest = json.loads(Path(options['manifest']).read_text())
            if set(manifest) != {'board_id', 'bindings', 'requests'}:
                raise ValueError('manifest keys')
            board = manifest['board_id']; cfg = board_config(board)
            if not cfg:
                raise ValueError('unknown board')
            bindings, requests = {}, []
            for item in manifest['bindings']:
                if set(item) != {'login','send_user_id','signer_email','role','enabled'}:
                    raise ValueError('binding keys')
                login = item['login']
                if not isinstance(login, str) or not login or login != login.strip().lower() or login in bindings:
                    raise ValueError('ambiguous login')
                if item['role'] not in {'reader','writer','manager'} or type(item['enabled']) is not bool:
                    raise ValueError('binding role/enabled')
                user = User.objects.get(pk=item['send_user_id'], is_active=True, is_staff=True)
                bindings[login] = (item, user)
            seen = set()
            for item in manifest['requests']:
                if set(item) != {'workflow_id','creator_login','task_ref'} or item['workflow_id'] in seen:
                    raise ValueError('request keys or duplicate workflow')
                seen.add(item['workflow_id'])
                if item['creator_login'] not in bindings or not bindings[item['creator_login']][0]['enabled']:
                    raise ValueError('unmapped creator')
                work = Workflow.objects.select_related('owner__signcredential','room').get(pk=item['workflow_id'])
                creator = bindings[item['creator_login']][1]
                legacy_request(work, board, item['task_ref'], creator=creator, apply=False)
                requests.append((item, work, creator))
        except (ValueError, TypeError, KeyError, AttributeError, ValidationError, User.DoesNotExist, Workflow.DoesNotExist) as exc:
            raise CommandError('Invalid or unmapped import manifest.') from exc
        if not options['apply']:
            self.stdout.write(f'Dry run: {len(bindings)} bindings, {len(requests)} requests; no changes or network reads.')
            return
        with transaction.atomic():
            for login, (item, user) in bindings.items():
                BoardStaffBinding.objects.update_or_create(board_id=board, login=login, defaults={
                    'send_user':user,'signer_email':item['signer_email'],'role':item['role'],'enabled':item['enabled']})
            for item, work, creator in requests:
                row = legacy_request(work, board, item['task_ref'], creator=creator)
                if options['fetch_audit']:
                    with Documenso(work.owner.signcredential) as client:
                        envelope = client.get(work.envelope_id)
                        validate_envelope(work, envelope)
                        for artifact in work.artifacts.filter(kind='sealed_pdf'):
                            snapshot_fields(work, artifact.sha256, artifact.item_id, envelope)
                        refresh_audit(row, client)
        self.stdout.write(f'Applied: {len(bindings)} bindings, {len(requests)} requests; legacy identity retained.')
