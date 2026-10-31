import hashlib
import hmac
import json
import time
import uuid
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
from django.conf import settings
from django.core import mail, signing
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Job, Company, JobSubmission, NewsletterSubscriber
from .payments import publish_submission
from scraper.persistence import refresh_scraped_job


class WorkflowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.company = Company.objects.create(name='Example Bank')
        self.form = dict(title='Analyst', company_name='Example Bank', contact_email='employer@example.com', location='Zürich', salary='', apply_link='https://example.com/apply', job_type='Permanent', description='An analyst role.\nApply now.', request_id=str(uuid.uuid4()))

    def order(self):
        data = {key: value for key, value in self.form.items() if key != 'request_id'}
        return JobSubmission.objects.create(**data, checkout_session_id='cs_test_order')

    def event(self, order, **overrides):
        session = dict(id=order.checkout_session_id, mode='payment', payment_status='paid', amount_total=19000, currency='chf', livemode=False, client_reference_id=str(order.id), metadata={'application': 'swissfinancejobs', 'submission_id': str(order.id)})
        session.update(overrides)
        return {'id': 'evt_example', 'type': 'checkout.session.completed', 'data': {'object': session}}

    def webhook(self, event, signature=None):
        body = json.dumps(event).encode()
        stamp = int(time.time())
        digest = hmac.new(settings.STRIPE_WEBHOOK_SECRET.encode(), str(stamp).encode() + b'.' + body, hashlib.sha256).hexdigest()
        return self.client.post('/api/stripe/webhook/', body, content_type='application/json', HTTP_STRIPE_SIGNATURE=signature or f't={stamp},v1={digest}')

    def test_public_cannot_create_job_or_send_unpaid_inquiry(self):
        self.assertEqual(self.client.post('/api/jobs/', {}, format='json').status_code, 405)
        self.assertEqual(self.client.post('/api/job-inquiries/', self.form, format='json').status_code, 404)
        self.assertEqual(Job.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(STRIPE_SECRET_KEY='sk_live_placeholder', STRIPE_LIVE_MODE=False)
    def test_mismatched_stripe_mode_disables_checkout(self):
        self.assertFalse(self.client.get('/api/checkout/config/').json()['available'])
        self.assertEqual(self.client.post('/api/checkout/', self.form, format='json').status_code, 503)
        self.assertEqual(JobSubmission.objects.count(), 0)

    @patch('jobs.payments.stripe_client')
    def test_checkout_price_is_server_controlled_and_retries_reuse_order(self, factory):
        create = factory.return_value.v1.checkout.sessions.create
        create.return_value = SimpleNamespace(id='cs_test_created', url='https://checkout.stripe.com/c/test')
        factory.return_value.v1.checkout.sessions.retrieve.return_value = SimpleNamespace(status='open')
        form = {**self.form, 'amount': 1}
        for _ in range(2):
            self.assertEqual(self.client.post('/api/checkout/', form, format='json').status_code, 200)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(create.call_args.args[0]['line_items'][0]['price_data']['unit_amount'], 19000)
        self.assertEqual(create.call_args.args[0]['managed_payments'], {'enabled': False})
        self.assertNotIn('payment_method_types', create.call_args.args[0])
        self.assertEqual(JobSubmission.objects.count(), 1)
        self.assertEqual(Job.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @patch('jobs.payments.stripe_client')
    def test_expired_checkout_can_restart_but_completed_checkout_cannot_charge_again(self, factory):
        order = self.order()
        form = {**self.form, 'request_id': str(order.id)}
        retrieve = factory.return_value.v1.checkout.sessions.retrieve
        retrieve.return_value = SimpleNamespace(status='expired')
        self.assertEqual(self.client.post('/api/checkout/', form, format='json').status_code, 410)
        retrieve.return_value = SimpleNamespace(status='complete')
        self.assertEqual(self.client.post('/api/checkout/', form, format='json').status_code, 409)
        factory.return_value.v1.checkout.sessions.create.assert_not_called()

    def test_webhook_rejects_unsigned_or_old_events(self):
        order = self.order()
        self.assertEqual(self.webhook(self.event(order), 'invalid').status_code, 400)
        order.refresh_from_db()
        self.assertIsNone(order.paid_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_paid_webhook_emails_once_and_does_not_publish(self):
        order = self.order()
        for _ in range(2):
            self.assertEqual(self.webhook(self.event(order)).status_code, 200)
        order.refresh_from_db()
        self.assertIsNotNone(order.paid_at)
        self.assertIsNotNone(order.notified_at)
        self.assertEqual(Job.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(str(order.id), mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [settings.JOB_REVIEW_EMAIL])

    def test_unpaid_wrong_amount_and_wrong_mode_do_not_fulfill(self):
        order = self.order()
        self.assertEqual(self.webhook(self.event(order, payment_status='unpaid')).status_code, 200)
        for fields in ({'amount_total': 1}, {'livemode': True}, {'currency': 'usd'}, {'client_reference_id': 'other'}, {'mode': 'subscription'}):
            self.assertEqual(self.webhook(self.event(order, **fields)).status_code, 400)
        order.refresh_from_db()
        self.assertIsNone(order.paid_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_keeps_payment_and_can_retry(self):
        order = self.order()
        with patch('jobs.payments.EmailMessage.send', side_effect=OSError('SMTP offline')):
            self.assertEqual(self.webhook(self.event(order)).status_code, 500)
        order.refresh_from_db()
        self.assertIsNotNone(order.paid_at)
        self.assertIsNone(order.notified_at)
        call_command('retry_notifications', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.webhook(self.event(order)).status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_only_paid_orders_can_publish_and_publication_is_idempotent(self):
        order = self.order()
        with self.assertRaises(ValueError):
            publish_submission(order.id)
        order.paid_at = timezone.now(); order.save()
        job, created = publish_submission(order.id)
        self.assertTrue(created)
        self.assertAlmostEqual((job.expires_at - job.posted_at).total_seconds(), 30 * 86400, delta=5)
        same, created = publish_submission(order.id)
        self.assertFalse(created)
        self.assertEqual(same.id, job.id)
        self.assertEqual(Job.objects.count(), 1)

    def test_status_never_exposes_employer_data(self):
        self.order()
        response = self.client.get('/api/checkout/status/?session_id=cs_test_order')
        self.assertEqual(response.json(), {'status': 'pending'})
        self.assertEqual(self.client.get('/api/checkout/status/?session_id=bad').status_code, 400)

    def test_listing_is_paginated_sanitized_and_query_count_is_bounded(self):
        for index in range(25):
            Job.objects.create(title=f'Job {index}', company=self.company, location='Zürich', description='Safe', apply_link='https://example.com')
        job = Job.objects.first()
        Job.objects.filter(pk=job.pk).update(description='<p onclick="alert(1)">Hello<img src=x onerror=alert(1)><a href="javascript:alert(1)">bad</a></p>')
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/api/jobs/')
        self.assertLessEqual(len(queries), 2)
        self.assertEqual(response.json()['count'], 25)
        self.assertEqual(len(response.json()['results']), 20)
        self.assertNotIn('description', response.json()['results'][0])
        detail = self.client.get(f'/api/jobs/{job.id}/').json()['description']
        for unsafe in ['onclick', 'onerror', 'javascript:', '<img']:
            self.assertNotIn(unsafe, detail)

    def test_filter_and_expiry_and_cleanup_preserve_records(self):
        job = Job.objects.create(title='Analyst', company=self.company, location='Zürich | Lugano', description='Finance', apply_link='https://example.com')
        self.assertEqual(self.client.get('/api/jobs/?location=Lugano&search=Finance').json()['count'], 1)
        Job.objects.filter(pk=job.pk).update(expires_at=timezone.now() - timedelta(days=1))
        self.assertEqual(self.client.get('/api/jobs/').json()['count'], 0)
        self.assertEqual(self.client.get(f'/api/jobs/{job.id}/').status_code, 404)
        call_command('cleanup_expired_jobs', stdout=StringIO())
        job.refresh_from_db(); self.assertTrue(job.is_active)
        call_command('cleanup_expired_jobs', apply=True, stdout=StringIO())
        job.refresh_from_db(); self.assertFalse(job.is_active)
        self.assertEqual(Job.objects.count(), 1)

    def test_refresh_scraper_never_changes_paid_listing(self):
        order = self.order(); order.paid_at = timezone.now(); order.save()
        job, _ = publish_submission(order.id)
        old_expiry = job.expires_at
        refresh_scraped_job(company=self.company, title=job.title, location=job.location, description='Scraped', apply_link=job.apply_link)
        job.refresh_from_db()
        self.assertNotEqual(job.description, 'Scraped')
        self.assertEqual(job.expires_at, old_expiry)

    def test_newsletter_requires_confirmation_and_supports_unsubscribe(self):
        response = self.client.post('/api/newsletter/subscribe/', {'email': 'reader@example.com'}, format='json')
        self.assertEqual(response.status_code, 200)
        subscriber = NewsletterSubscriber.objects.get()
        self.assertFalse(subscriber.is_active)
        self.assertEqual(len(mail.outbox), 1)
        token = signing.dumps(str(subscriber.unsubscribe_token), salt='newsletter-confirm')
        self.assertEqual(self.client.post('/api/newsletter/confirm/', {'token': token}, format='json').status_code, 200)
        subscriber.refresh_from_db(); self.assertTrue(subscriber.is_active)
        self.assertEqual(self.client.post('/api/newsletter/unsubscribe/', {'token': str(subscriber.unsubscribe_token)}, format='json').status_code, 200)
        subscriber.refresh_from_db(); self.assertFalse(subscriber.is_active)

    def test_weekly_newsletter_is_opt_in_and_retry_safe(self):
        active = NewsletterSubscriber.objects.create(email='active@example.com', is_active=True, confirmed_at=timezone.now())
        NewsletterSubscriber.objects.create(email='pending@example.com')
        Job.objects.create(title='Analyst', company=self.company, location='Zürich', description='Finance', apply_link='https://example.com')
        call_command('send_newsletter', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)
        for _ in range(2):
            call_command('send_newsletter', send=True, stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [active.email])
        self.assertIn(str(active.unsubscribe_token), mail.outbox[0].body)
