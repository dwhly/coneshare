import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from dealroom_sign.workflows import sweep


class Command(BaseCommand):
    help = 'Recover durable signing workflows and reconcile pending envelopes every 15 seconds.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')

    def handle(self, *args, **options):
        while True:
            start = time.monotonic()
            close_old_connections()
            sweep()
            if options['once']:
                return
            time.sleep(max(0, 15 - (time.monotonic() - start)))
