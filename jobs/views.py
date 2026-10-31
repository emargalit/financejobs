import logging
import stripe
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .models import Job, Company, JobSubmission, NewsletterSubscriber
from .serializers import JobSerializer, JobListSerializer, JobInquirySerializer, CompanySerializer
from .payments import create_checkout, record_payment, notify_submission, retrieve_checkout, checkout_available

logger = logging.getLogger(__name__)


def active_jobs():
    return Job.objects.filter(is_active=True, expires_at__gt=timezone.now()).select_related('company').annotate(listed_on=Coalesce('source_posted_at', TruncDate('posted_at'))).order_by('-listed_on', '-posted_at', '-id')


class JobPagination(PageNumberPagination):
    page_size = 20


class JobListAPIView(generics.ListAPIView):
    serializer_class = JobListSerializer
    pagination_class = JobPagination
    filter_backends = [SearchFilter]
    search_fields = ['title', 'company__name', 'location', 'description']

    def get_queryset(self):
        jobs = active_jobs()
        for field in ('job_type', 'company__name'):
            value = self.request.query_params.get('company' if field == 'company__name' else field)
            if value:
                jobs = jobs.filter(**{field: value})
        location = self.request.query_params.get('location')
        if location:
            jobs = jobs.filter(Q(location=location) | Q(location__startswith=location + ' | ') | Q(location__endswith=' | ' + location) | Q(location__contains=' | ' + location + ' | '))
        return jobs


class JobRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = JobSerializer

    def get_queryset(self):
        return active_jobs()


class JobFiltersView(APIView):
    def get(self, request):
        jobs = active_jobs().order_by()
        locations = sorted({part.strip() for location in jobs.values_list('location', flat=True).distinct() for part in location.split('|') if part.strip()})
        companies = list(jobs.exclude(company=None).values_list('company__name', flat=True).distinct().order_by('company__name'))
        return Response({'locations': locations, 'companies': companies})


class CompanyListAPIView(generics.ListAPIView):
    queryset = Company.objects.all().order_by('name')
    serializer_class = CompanySerializer
    pagination_class = JobPagination


class CheckoutConfigView(APIView):
    def get(self, request):
        return Response({'amount': settings.JOB_AD_AMOUNT, 'currency': 'chf', 'days': 30,
                         'available': checkout_available(),
                         'contact_email': settings.JOB_REVIEW_EMAIL})


class CheckoutView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'checkout'

    def post(self, request):
        if not checkout_available():
            return Response({'detail': 'Online payment is temporarily unavailable. Please try again later.'}, status=503)
        serializer = JobInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        request_id = data.pop('request_id')
        try:
            with transaction.atomic():
                submission, _ = JobSubmission.objects.get_or_create(id=request_id, defaults={**data, 'amount': settings.JOB_AD_AMOUNT})
                submission = JobSubmission.objects.select_for_update().get(pk=submission.id)
                if any(getattr(submission, key) != value for key, value in data.items()):
                    return Response({'detail': 'This checkout belongs to different details. Please start a new submission.'}, status=409)
                if submission.paid_at:
                    return Response({'detail': 'This advertisement has already been paid for.'}, status=409)
                if submission.checkout_session_id:
                    current = retrieve_checkout(submission.checkout_session_id)
                    if current.status == 'expired':
                        return Response({'detail': 'This checkout has expired. Your draft is saved; press Continue to payment again to start a new checkout.'}, status=410)
                    if current.status == 'complete':
                        return Response({'detail': 'Checkout is already complete. Please wait for payment confirmation; do not pay again.'}, status=409)
                if not submission.checkout_session_id:
                    session = create_checkout(submission)
                    submission.checkout_session_id = session.id
                    submission.checkout_url = session.url
                    submission.save(update_fields=['checkout_session_id', 'checkout_url'])
                return Response({'url': submission.checkout_url})
        except stripe.StripeError:
            logger.exception('Stripe checkout creation failed')
            return Response({'detail': 'Unable to open payment. Please retry; your form has been kept.'}, status=502)


class PaymentStatusView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'payment_status'

    def get(self, request):
        session_id = request.query_params.get('session_id', '')
        if not session_id.startswith('cs_') or len(session_id) > 255:
            return Response({'detail': 'Invalid payment reference.'}, status=400)
        submission = JobSubmission.objects.filter(checkout_session_id=session_id).first()
        if not submission:
            return Response({'detail': 'Payment reference not found.'}, status=404)
        # No private form or customer information is exposed.
        return Response({'status': 'published' if submission.published_at else 'paid' if submission.paid_at else 'pending'})


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET:
            return Response(status=503)
        try:
            event = stripe.Webhook.construct_event(request.body, request.META.get('HTTP_STRIPE_SIGNATURE', ''), settings.STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.SignatureVerificationError):
            return Response(status=400)
        if event['type'] not in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
            return Response({'received': True})
        try:
            submission_id = record_payment(event['data']['object'])
            if submission_id:
                notify_submission(submission_id)
        except ValueError:
            logger.exception('Payment does not match order')
            return Response(status=400)
        except Exception:
            # Payment is durable even when email fails; Stripe retries and the
            # retry_notifications command can recover after the retry window.
            logger.exception('Payment fulfillment failed; retry required')
            return Response(status=500)
        return Response({'received': True})


class NewsletterEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class NewsletterSubscribeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'newsletter'

    def post(self, request):
        serializer = NewsletterEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber, _ = NewsletterSubscriber.objects.get_or_create(email=serializer.validated_data['email'].lower())
        if not subscriber.is_active:
            token = signing.dumps(str(subscriber.unsubscribe_token), salt='newsletter-confirm')
            link = settings.FRONTEND_URL + '/newsletter/confirm?token=' + token
            try:
                send_mail('Confirm your Swiss Finance Jobs subscription', f'Confirm your weekly job newsletter subscription:\n{link}\n\nIf you did not request this, ignore this email.', settings.DEFAULT_FROM_EMAIL, [subscriber.email])
            except Exception:
                logger.exception('Newsletter confirmation email failed')
                return Response({'detail': 'Unable to send confirmation. Please try again later.'}, status=503)
        return Response({'detail': 'If confirmation is needed, an email has been sent. Please check your inbox.'})


class NewsletterConfirmView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'newsletter'

    def post(self, request):
        try:
            token = signing.loads(request.data.get('token', ''), salt='newsletter-confirm', max_age=86400)
            subscriber = NewsletterSubscriber.objects.get(unsubscribe_token=token)
        except (signing.BadSignature, NewsletterSubscriber.DoesNotExist, ValueError):
            return Response({'detail': 'This confirmation link is invalid or expired. Please subscribe again.'}, status=400)
        subscriber.is_active = True
        subscriber.confirmed_at = timezone.now()
        subscriber.save(update_fields=['is_active', 'confirmed_at'])
        return Response({'detail': 'Your newsletter subscription is confirmed.'})


class NewsletterUnsubscribeView(APIView):
    def post(self, request):
        token = serializers.UUIDField().run_validation(request.data.get('token'))
        NewsletterSubscriber.objects.filter(unsubscribe_token=token).update(is_active=False)
        return Response({'detail': 'You have been unsubscribed.'})


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return Response({'status': 'ok'})
