"""Operator-only, dry-run by default; only orphaned content-addressed S2 files."""
import re
import time
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from datarooms.models import Dataroom
from documents.models import DocumentVersion
from dealroom.models import BoardRoom


class Command(BaseCommand):
    help = 'List old unreferenced Board import files under an explicitly selected core storage root.'

    def add_arguments(self, parser):
        parser.add_argument('--storage-root', required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        root = Path(options['storage_root']).resolve(strict=True)
        if not root.is_dir():
            raise CommandError('Storage root must be a directory.')
        count = 0
        for path in root.glob('*/board-import/*/*/*'):
            if path.is_symlink() or not path.is_file() or time.time()-path.stat().st_mtime < 86400:
                continue
            parts = path.relative_to(root).parts
            if len(parts) != 5 or not all(re.fullmatch('[0-9a-f]{64}', part) for part in parts[-2:]):
                continue
            if not path.resolve().is_relative_to(root):
                continue
            key = path.relative_to(root).as_posix()
            with transaction.atomic():
                room = Dataroom.objects.select_for_update().filter(pk=parts[2]).first()
                if room and BoardRoom.objects.filter(room=room).exclude(staged_import='').exists():
                    continue
                if DocumentVersion.objects.filter(Q(original_storage_key=key) | Q(storage_key=key)).exists():
                    continue
                if options['apply']:
                    path.unlink()
                count += 1
        self.stdout.write(f'{count} orphaned import files '+('removed.' if options['apply'] else 'eligible; dry run.'))
