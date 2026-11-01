"""Manual invoice requests: no invoice issuance or payment is inferred here."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMessage
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from .models import JobSubmission


def notify_invoice_request(submission_id):
    with transaction.atomic():
        submission = JobSubmission.objects.select_for_update().get(pk=submission_id)
        if submission.payment_method != 'invoice' or submission.invoice_notified_at:
            return False
        review_url = settings.BACKEND_URL + reverse('admin:jobs_jobsubmission_change', args=[submission.id])
        body = '\n'.join([
            'An employer requested an invoice. This request is not proof of payment.',
            f'Order: {submission.id}', f'Amount: {submission.amount / 100:.2f} {submission.currency.upper()}',
            f'Bill to: {submission.billing_name}', f'Billing address: {submission.billing_address}',
            f'Send invoice to: {submission.billing_email}', f'Contact: {submission.contact_email}',
            f'Company: {submission.company_name}', f'Title: {submission.title}',
            f'Location: {submission.location}', f'Job type: {submission.job_type}',
            f'Salary: {submission.salary}', f'Apply link: {submission.apply_link}', '', submission.description, '',
            f'Review: {review_url}',
            'Send the invoice manually and save its reference in admin. After receiving payment, select',
            '"Confirm payment received for selected invoices" then "Publish selected paid advertisements (30 days)".',
            'Publish within 2 hours of receiving payment. The 30 days start at publication.',
        ])
        sent = EmailMessage(
            subject=f'Invoice requested: {submission.title}'.replace('\r', ' ').replace('\n', ' '),
            body=body, from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.JOB_REVIEW_EMAIL], reply_to=[submission.contact_email],
        ).send(fail_silently=False)
        if sent != 1:
            raise RuntimeError('Invoice notification was not accepted by the mail backend')
        submission.invoice_notified_at = timezone.now()
        submission.save(update_fields=['invoice_notified_at'])
        return True


def confirm_invoice_payment(submission_id, actor):
    if not actor.is_active or not actor.is_staff or not actor.has_perm('jobs.change_jobsubmission'):
        raise PermissionDenied('Only authorized staff can confirm invoice payment.')
    with transaction.atomic():
        submission = JobSubmission.objects.select_for_update().get(pk=submission_id)
        if submission.payment_method != 'invoice':
            raise ValueError('Only invoice requests can be marked as paid manually. Stripe payments are confirmed automatically.')
        if not submission.invoice_reference.strip():
            raise ValueError('Save the invoice reference before confirming receipt of payment.')
        if submission.paid_at:
            return False
        submission.paid_at = timezone.now()
        submission.invoice_paid_by = actor
        submission.save(update_fields=['paid_at', 'invoice_paid_by'])
        return True
