from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Validate the vontobel careers feed. Pass --apply to publish.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        call_command('refresh_jobs', source=['vontobel'], apply=options['apply'])
