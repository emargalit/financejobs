from .settings import *

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
STRIPE_SECRET_KEY = 'sk_test_placeholder'
STRIPE_WEBHOOK_SECRET = 'whsec_test_only'
STRIPE_LIVE_MODE = False
ALLOWED_HOSTS = ['testserver', 'localhost']
FRONTEND_URL = 'https://jobs.example.com'
BACKEND_URL = 'https://api.example.com'
STATICFILES_DIRS = []

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
