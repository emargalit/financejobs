from django.core.management.base import BaseCommand, CommandError
from jobs.models import JobSubmission
from jobs.payments import notify_submission

class Command(BaseCommand):
    help = 'Retry paid-ad notifications that have not been delivered.'

    def handle(self, *args, **options):
        failures = 0
        for submission in JobSubmission.objects.filter(paid_at__isnull=False, notified_at__isnull=True):
            try:
                notify_submission(submission.id)
                self.stdout.write(f'Notified order {submission.id}')
            except Exception:
                failures += 1
                self.stderr.write(f'Notification failed for order {submission.id}')
        if failures:
            raise CommandError(f'{failures} notifications failed; retry after fixing email delivery.')
