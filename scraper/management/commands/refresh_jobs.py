from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from jobs.models import Job

SOURCES = {'pictet': 'scrape_pictet', 'lgt': 'scrape_lgt', 'ubs': 'scrape_ubs', 'julius': 'scrape_julius', 'efinancialcareers': 'scrape_jobs'}

class Command(BaseCommand):
    help = 'Run headless scrapers and fail visibly when a source refreshes no listings.'

    def add_arguments(self, parser):
        parser.add_argument('--source', choices=SOURCES, action='append')

    def handle(self, *args, **options):
        failed = []
        for source in options['source'] or SOURCES:
            started = timezone.now()
            try:
                call_command(SOURCES[source])
                refreshed = Job.objects.filter(last_seen_at__gte=started).count()
                if not refreshed:
                    raise CommandError('No jobs refreshed; verify selectors and source availability.')
                self.stdout.write(f'{source}: refreshed {refreshed} jobs')
            except Exception as error:
                failed.append(source)
                self.stderr.write(f'{source}: {error}')
        call_command('cleanup_expired_jobs', apply=True)
        if failed:
            raise CommandError('Refresh failed for: ' + ', '.join(failed))
