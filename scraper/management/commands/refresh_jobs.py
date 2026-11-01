import json
from dataclasses import asdict
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from scraper.sources import SOURCES, collect
from scraper.persistence import publish_source
from scraper.roles import classify_role


class Command(BaseCommand):
    help = 'Validate five official Swiss careers feeds; publish with --apply. Failed feeds leave their listings untouched.'

    def add_arguments(self, parser):
        parser.add_argument('--source', choices=SOURCES, action='append')
        parser.add_argument('--apply', action='store_true', help='Publish the validated feed and archive missing source jobs.')
        parser.add_argument('--export', help='Write validated listings as JSON for review (not a database backup).')

    def handle(self, *args, **options):
        failed, exported = [], []
        for source in options['source'] or SOURCES:
            self.stdout.write(f'{source}: fetching official careers feed...', ending='\n')
            self.stdout.flush()
            try:
                listings = collect(source)
                exported.extend(asdict(job) for job in listings)
                report = publish_source(source, listings) if options['apply'] else {'validated': len(listings), 'eligible': sum(classify_role(job.title).include for job in listings), 'excluded': sum(not classify_role(job.title).include for job in listings), 'published': False}
                self.stdout.write(f'{source}: {json.dumps(report)}')
                self.stdout.flush()
            except Exception as error:
                failed.append(source)
                self.stderr.write(f'{source}: {type(error).__name__}: {error}')
                self.stderr.flush()
        if options['export']:
            Path(options['export']).write_text(json.dumps(exported, ensure_ascii=False, indent=2))
        if failed:
            raise CommandError('Feeds not updated: ' + ', '.join(failed))
        self.stdout.write(self.style.SUCCESS('All requested feeds validated' + (' and published.' if options['apply'] else '. Dry run; nothing published.')))
