from django.contrib import admin, messages
from .models import Job, Company, JobSubmission, NewsletterSubscriber
from .payments import publish_submission, notify_submission
from .invoices import confirm_invoice_payment, notify_invoice_request


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_type')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type', 'is_active', 'expires_at')
    list_filter = ('is_active', 'job_type', 'company')
    search_fields = ('title', 'company__name', 'location')


@admin.register(JobSubmission)
class JobSubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'company_name', 'contact_email', 'payment_method', 'invoice_reference', 'paid_at', 'published_at')
    list_filter = ('payment_method', 'paid_at', 'published_at')
    search_fields = ('title', 'company_name', 'contact_email')
    readonly_fields = ('payment_method', 'invoice_paid_by', 'invoice_notified_at', 'id', 'amount', 'currency', 'checkout_session_id', 'checkout_url', 'paid_at', 'notified_at', 'published_at', 'job', 'created_at')
    actions = ['confirm_invoice_paid', 'publish_paid', 'retry_email']

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (('invoice_reference',) if obj and obj.paid_at else ())

    @admin.action(description='Confirm payment received for selected invoices', permissions=['change'])
    def confirm_invoice_paid(self, request, queryset):
        for submission in queryset:
            try:
                changed = confirm_invoice_payment(submission.id, request.user)
                if changed:
                    self.log_change(request, submission, 'Confirmed receipt of invoice payment: ' + submission.invoice_reference)
                self.message_user(request, f'{submission.title}: ' + ('payment recorded. You can now publish the ad.' if changed else 'payment already recorded.'))
            except ValueError as error:
                self.message_user(request, str(error), level=messages.ERROR)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='Publish selected paid advertisements (30 days)')
    def publish_paid(self, request, queryset):
        for submission in queryset:
            try:
                _, created = publish_submission(submission.id)
                self.message_user(request, f'{submission.title}: ' + ('published.' if created else 'already published.'))
            except ValueError as error:
                self.message_user(request, str(error), level=messages.ERROR)

    @admin.action(description='Retry unsent invoice requests and paid-ad notifications')
    def retry_email(self, request, queryset):
        for submission in queryset:
            try:
                if submission.payment_method == 'invoice':
                    notify_invoice_request(submission.id)
                if submission.paid_at:
                    notify_submission(submission.id)
            except Exception:
                self.message_user(request, 'Email delivery failed. Check the server email configuration.', level=messages.ERROR)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'confirmed_at', 'created_at')
    readonly_fields = ('unsubscribe_token', 'confirmed_at')
    list_filter = ('is_active',)
