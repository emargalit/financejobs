from django.conf import settings
from django.core.checks import Error, Warning, register


@register(deploy=True)
def payment_deployment_checks(app_configs, **kwargs):
    issues = []
    if settings.DEBUG:
        return issues  # Django's built-in deployment check already reports this.
    if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        issues.append(Error('Production requires PostgreSQL for durable orders and concurrent payment processing.', id='jobs.E001'))
    if settings.STRIPE_SECRET_KEY:
        expected = ('sk_live_', 'rk_live_') if settings.STRIPE_LIVE_MODE else ('sk_test_', 'rk_test_')
        if not settings.STRIPE_SECRET_KEY.startswith(expected):
            issues.append(Error('STRIPE_SECRET_KEY does not match STRIPE_LIVE_MODE.', id='jobs.E002'))
        if not settings.STRIPE_WEBHOOK_SECRET:
            issues.append(Error('Configure STRIPE_WEBHOOK_SECRET before enabling checkout.', id='jobs.E003'))
    else:
        issues.append(Warning('Stripe is not configured; checkout remains disabled.', id='jobs.W001'))
    if not settings.DEFAULT_FROM_EMAIL:
        issues.append(Error('Configure DEFAULT_FROM_EMAIL for paid-ad notifications.', id='jobs.E004'))
    for name in ('FRONTEND_URL', 'BACKEND_URL'):
        if not getattr(settings, name).startswith('https://'):
            issues.append(Error(f'{name} must use HTTPS in production.', id='jobs.E005'))
    return issues
