from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from jobs.models import NewsletterSubscriber, NewsletterDelivery
from jobs.views import active_jobs

class Command(BaseCommand):
    help = 'Send this week\'s new jobs to confirmed subscribers (dry run by default).'

    def add_arguments(self, parser):
        parser.add_argument('--send', action='store_true')

    def handle(self, *args, **options):
        today = timezone.localdate()
        week = today - timedelta(days=today.weekday())
        jobs = list(active_jobs().filter(posted_at__gte=timezone.now() - timedelta(days=7))[:20])
        if not jobs:
            self.stdout.write('No new jobs; nothing sent.')
            return
        subscribers = NewsletterSubscriber.objects.filter(is_active=True, confirmed_at__isnull=False)
        if not options['send']:
            self.stdout.write(f'Dry run: {len(jobs)} jobs, {subscribers.count()} confirmed subscribers. Use --send to deliver.')
            return
        failures = 0
        for subscriber in subscribers:
            try:
                with transaction.atomic():
                    subscriber = NewsletterSubscriber.objects.select_for_update().get(pk=subscriber.pk)
                    if not subscriber.is_active:
                        continue
                    delivery, _ = NewsletterDelivery.objects.get_or_create(subscriber=subscriber, week=week)
                    if delivery.sent_at:
                        continue
                    unsubscribe = settings.FRONTEND_URL + '/newsletter/unsubscribe?token=' + str(subscriber.unsubscribe_token)
                    lines = ['This week on Swiss Finance Jobs', '']
                    for job in jobs:
                        lines += [f'{job.title} — {job.company.name if job.company else ""} — {job.location}', f'{settings.FRONTEND_URL}/jobs/{job.id}', '']
                    lines += [f'Unsubscribe: {unsubscribe}']
                    EmailMessage('Your weekly Swiss Finance Jobs', '\n'.join(lines), settings.DEFAULT_FROM_EMAIL, [subscriber.email], headers={'List-Unsubscribe': f'<{unsubscribe}>'}).send()
                    delivery.sent_at = timezone.now()
                    delivery.save(update_fields=['sent_at'])
            except Exception:
                failures += 1
        if failures:
            raise CommandError(f'{failures} deliveries failed. Retry this command to send only outstanding messages.')
