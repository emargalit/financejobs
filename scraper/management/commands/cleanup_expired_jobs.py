from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job

class Command(BaseCommand):
    help = 'Archive expired listings without deleting records. Dry run by default.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Archive the expired listings.')

    def handle(self, *args, **options):
        jobs = Job.objects.filter(is_active=True, expires_at__lte=timezone.now())
        if options['apply']:
            self.stdout.write(f'Archived {jobs.update(is_active=False)} expired jobs. No records deleted.')
        else:
            self.stdout.write(f'Dry run: {jobs.count()} expired jobs. Use --apply to archive them.')
