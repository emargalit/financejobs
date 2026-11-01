from django.core.management.base import BaseCommand, CommandError
from jobs.models import JobSubmission
from jobs.payments import notify_submission
from jobs.invoices import notify_invoice_request

class Command(BaseCommand):
    help = 'Retry invoice-request and paid-ad notifications that have not been delivered.'

    def handle(self, *args, **options):
        failures = 0
        for submission in JobSubmission.objects.filter(paid_at__isnull=False, notified_at__isnull=True):
            try:
                notify_submission(submission.id)
                self.stdout.write(f'Notified order {submission.id}')
            except Exception:
                failures += 1
                self.stderr.write(f'Notification failed for order {submission.id}')
        for submission in JobSubmission.objects.filter(payment_method='invoice', invoice_notified_at__isnull=True):
            try:
                notify_invoice_request(submission.id)
                self.stdout.write(f'Notified invoice request {submission.id}')
            except Exception:
                failures += 1
                self.stderr.write(f'Invoice notification failed for order {submission.id}')
        if failures:
            raise CommandError(f'{failures} notifications failed; retry after fixing email delivery.')
