"""Reapply editorial scope without fetching feeds or renewing listing dates."""
import json
from collections import Counter
from django.core.management.base import BaseCommand
from django.db import transaction
from jobs.models import Company, Job
from scraper.roles import classify_role
from scraper.sources import SOURCES


class Command(BaseCommand):
    help = 'Preview unrelated imported jobs to archive; pass --apply to hide them. Never deletes records or changes paid ads.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--details', action='store_true', help='List excluded job IDs, titles and reasons.')

    def handle(self, *args, **options):
        with transaction.atomic():
            # Same institution locks as the importer; do not race a refresh.
            list(Company.objects.filter(name__in=[v[0] for v in SOURCES.values()]).order_by('pk').select_for_update())
            jobs = Job.objects.filter(source__in=SOURCES, is_active=True, jobsubmission__isnull=True)
            excluded = []
            checked = 0
            for job in jobs.only('id', 'title', 'source'):
                checked += 1
                decision = classify_role(job.title)
                if not decision.include:
                    excluded.append({'id': job.pk, 'title': job.title, 'source': job.source, 'reason': decision.reason})
            archived = jobs.filter(pk__in=[j['id'] for j in excluded]).update(is_active=False) if options['apply'] else 0
        if options['details']:
            for row in excluded:
                self.stdout.write(json.dumps(row, ensure_ascii=False))
        self.stdout.write(json.dumps({'checked': checked, 'eligible': checked - len(excluded), 'excluded': len(excluded), 'reasons': dict(Counter(j['reason'] for j in excluded)), 'archived': archived, 'applied': options['apply']}))
