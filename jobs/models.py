import uuid
from django.conf import settings
from datetime import timedelta
from django.db import models
from django.utils import timezone
from .content import clean_description, normalize_job_type


def listing_expiry():
    return timezone.now() + timedelta(days=30)


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    company_type = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    location = models.CharField(max_length=255)
    salary = models.CharField(max_length=255, blank=True, null=True)
    apply_link = models.URLField(max_length=500)
    posted_at = models.DateTimeField(auto_now_add=True)
    job_type = models.CharField(max_length=100, blank=True)
    expires_at = models.DateTimeField(default=listing_expiry, db_index=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=35, blank=True, db_index=True)
    source_job_id = models.CharField(max_length=150, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    source_posted_at = models.DateField(null=True, blank=True)
    work_schedule = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['source', 'source_job_id'], condition=~models.Q(source=''), name='unique_employer_source_job'),
            models.UniqueConstraint(fields=['title', 'company', 'location'], condition=models.Q(source=''), name='unique_direct_job_title_location'),
        ]

    def save(self, *args, **kwargs):
        self.description = clean_description(self.description)
        self.job_type = normalize_job_type(self.job_type)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class JobSubmission(models.Model):
    """Private advertisement order; never appears in the public jobs API."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    company_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    location = models.CharField(max_length=255)
    salary = models.CharField(max_length=255, blank=True)
    apply_link = models.URLField(max_length=500)
    job_type = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=10, choices=[('stripe', 'Stripe'), ('invoice', 'Invoice')], default='stripe')
    billing_name = models.CharField(max_length=255, blank=True)
    billing_address = models.TextField(blank=True)
    billing_email = models.EmailField(blank=True)
    invoice_reference = models.CharField(max_length=150, blank=True, help_text='Enter the invoice number before confirming receipt of payment.')
    invoice_notified_at = models.DateTimeField(null=True, blank=True)
    invoice_paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.PositiveIntegerField(default=19000)
    currency = models.CharField(max_length=3, default='chf')
    checkout_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    checkout_url = models.URLField(max_length=2048, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    job = models.OneToOneField(Job, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.company_name}: {self.title}'


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.email


class NewsletterDelivery(models.Model):
    subscriber = models.ForeignKey(NewsletterSubscriber, on_delete=models.CASCADE)
    week = models.DateField()
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['subscriber', 'week'], name='unique_weekly_delivery')]
