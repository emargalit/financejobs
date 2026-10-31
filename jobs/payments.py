from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
import stripe
from .models import Company, Job, JobSubmission


def checkout_available():
    prefixes = ('sk_live_', 'rk_live_') if settings.STRIPE_LIVE_MODE else ('sk_test_', 'rk_test_')
    return bool(settings.STRIPE_SECRET_KEY.startswith(prefixes) and settings.STRIPE_WEBHOOK_SECRET)


def stripe_client():
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY, max_network_retries=1, http_client=stripe.RequestsClient(timeout=10))


def retrieve_checkout(session_id):
    return stripe_client().v1.checkout.sessions.retrieve(session_id)


def create_checkout(submission):
    return stripe_client().v1.checkout.sessions.create({
        'mode': 'payment',
        'payment_method_types': ['card'],
        'client_reference_id': str(submission.id),
        'customer_email': submission.contact_email,
        'metadata': {'submission_id': str(submission.id), 'application': 'swissfinancejobs'},
        'line_items': [{'quantity': 1, 'price_data': {
            'currency': submission.currency, 'unit_amount': submission.amount,
            'product_data': {'name': 'Swiss Finance Jobs — 30-day job advertisement'},
        }}],
        'success_url': settings.FRONTEND_URL + '/payment-result?session_id={CHECKOUT_SESSION_ID}',
        'cancel_url': settings.FRONTEND_URL + '/post-job?cancelled=1',
    }, options={'idempotency_key': f'job-ad-{submission.id}'})


def record_payment(session):
    if session.get('metadata', {}).get('application') != 'swissfinancejobs':
        return None
    if session.get('payment_status') != 'paid':
        return None
    with transaction.atomic():
        submission = JobSubmission.objects.select_for_update().get(checkout_session_id=session['id'])
        if (session.get('mode') != 'payment'
                or session.get('client_reference_id') != str(submission.id)
                or session.get('metadata', {}).get('submission_id') != str(submission.id)
                or session.get('amount_total') != submission.amount
                or session.get('currency') != submission.currency
                or session.get('livemode') != settings.STRIPE_LIVE_MODE):
            raise ValueError('Checkout session does not match the saved order.')
        if not submission.paid_at:
            submission.paid_at = timezone.now()
            submission.save(update_fields=['paid_at'])
    return submission.id


def notify_submission(submission_id):
    # Serialize duplicate deliveries. SMTP is at-least-once: a process crash after
    # SMTP accepts a message but before commit can produce a duplicate email.
    with transaction.atomic():
        submission = JobSubmission.objects.select_for_update().get(pk=submission_id)
        if not submission.paid_at or submission.notified_at:
            return False
        review_url = settings.BACKEND_URL + reverse('admin:jobs_jobsubmission_change', args=[submission.id])
        body = '\n'.join([
            'Payment confirmed. This ad is awaiting your manual review and publication.',
            f'Order: {submission.id}', f'Paid: {submission.amount / 100:.2f} {submission.currency.upper()}',
            f'Company: {submission.company_name}', f'Contact: {submission.contact_email}',
            f'Title: {submission.title}', f'Location: {submission.location}',
            f'Job type: {submission.job_type}', f'Salary: {submission.salary}',
            f'Apply link: {submission.apply_link}', '', submission.description, '',
            f'Review and publish: {review_url}',
            'The 30-day listing period starts when you publish.',
        ])
        EmailMessage(
            subject=f'Paid job advertisement: {submission.title}'.replace('\n', ' ').replace('\r', ' '),
            body=body, from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.JOB_REVIEW_EMAIL], reply_to=[submission.contact_email],
        ).send(fail_silently=False)
        submission.notified_at = timezone.now()
        submission.save(update_fields=['notified_at'])
        return True


def publish_submission(submission_id):
    with transaction.atomic():
        submission = JobSubmission.objects.select_for_update().get(pk=submission_id)
        if not submission.paid_at:
            raise ValueError('Only paid submissions can be published.')
        if submission.job_id:
            return submission.job, False
        company, _ = Company.objects.get_or_create(name=submission.company_name)
        # Do not overwrite an existing listing or consume a paid order silently.
        if Job.objects.filter(title=submission.title, company=company, location=submission.location).exists():
            raise ValueError('A matching job already exists. Review that listing before publishing this order.')
        job = Job.objects.create(
            title=submission.title, company=company, location=submission.location,
            description='<p>' + escape(submission.description).replace('\n', '<br>') + '</p>',
            salary=submission.salary, job_type=submission.job_type, apply_link=submission.apply_link,
            expires_at=timezone.now() + timedelta(days=30),
        )
        submission.job = job
        submission.published_at = timezone.now()
        submission.save(update_fields=['job', 'published_at'])
        return job, True
