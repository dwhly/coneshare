import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from drf_spectacular.generators import SchemaGenerator
from dealroom.registry import classify, operation_id


def inventory():
    generator = SchemaGenerator()
    generator._initialise_endpoints()
    entries = {}
    for path, regex, method, callback in generator.endpoints:
        view = generator.create_view(callback, method, None)
        entry = classify(view, method)
        entry.update(path=path, method=method)
        oid = operation_id(view, method)
        if oid in entries and entries[oid] != entry:
            raise CommandError(f'Duplicate operation ID: {oid}')
        entries[oid] = entry
    return dict(sorted(entries.items()))


class Command(BaseCommand):
    help = 'Verify or write the complete served DRF operation inventory (including exclusions).'
    def add_arguments(self, parser):
        parser.add_argument('--write', action='store_true')
    def handle(self, *args, **options):
        entries = inventory()
        path = Path(__file__).parents[2] / 'operations.json'
        text = json.dumps(entries, indent=2, sort_keys=True) + '\n'
        if options['write']:
            path.write_text(text)
        elif not path.exists() or path.read_text() != text:
            raise CommandError('Served routes differ from reviewed operation registry.')
        self.stdout.write(f'{len(entries)} operations inventoried; {sum(e["boundary"] == "staff" for e in entries.values())} staff operations.')
