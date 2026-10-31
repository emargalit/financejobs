# Swiss Finance Jobs

Django/DRF API, React job board, Stripe Checkout for employer advertisements,
manual publication in Django admin, and Playwright import commands.

## Development

Use Python 3.12 and Node 22. Create a virtualenv, install `requirements.txt`, and
copy `.env.example` to `.env` with a new random `SECRET_KEY`. Never commit `.env`.
Run `python manage.py migrate`, `python manage.py createsuperuser`, and
`python manage.py runserver`. In `financejobs-frontend`, run `npm ci`, copy
`.env.example` to `.env`, then run `npm start`.

Checks:

```sh
python manage.py test --settings=backend.test_settings
python manage.py makemigrations --check --dry-run
npm --prefix financejobs-frontend test -- --watchAll=false --runInBand
npm --prefix financejobs-frontend run build
```

Tests use an isolated SQLite database and in-memory email. They never charge a
card, contact Stripe, send real email, or modify your job database.

The GitHub Actions configuration is in `ci/checks.yml.example`. To activate CI,
copy it to `.github/workflows/checks.yml` using a credential authorized for
workflows. The current publishing credential lacks that scope; CI is not yet active.

## Paid advertisement workflow

1. Employer enters the ad. A private order is saved before Stripe Checkout opens.
2. Server sets the price (default CHF 390); the browser cannot choose it.
3. A signature-verified Stripe webhook checks payment status, amount, currency,
   account mode, and order references. A success-page visit cannot mark an order paid.
4. Paid orders are saved and emailed to `JOB_REVIEW_EMAIL`, with all ad details,
   the employer's reply-to address, and an admin review link.
5. In `/admin/jobs/jobsubmission/`, review/edit the ad, select it, and choose
   **Publish selected paid advertisements (30 days)**. Only paid orders can be
   published; repeat actions cannot publish twice. Existing matching jobs require
   manual review rather than silently overwriting a listing.
6. Publication starts the 30-day window. Expired jobs disappear from the public
   API automatically. Cleanup archives expired jobs without deleting records.

Only checkout status is public; submission/contact details remain private.
Duplicate Stripe deliveries do not normally repeat emails. SMTP provides
at-least-once delivery: a crash after SMTP accepts mail but before the database
commit may duplicate the notification. Use the order ID to identify it. Payment
is persisted before notification, so SMTP failures cannot lose a paid order.

Recover failed notifications with `python manage.py retry_notifications` or
with the admin action. Stripe also retries failed webhook deliveries. Refunds
are handled manually in Stripe after reviewing the order; refunds do not
currently remove or modify a published job automatically.

## Stripe setup

Use the separate Swiss Finance Jobs account. Start in a sandbox/test mode.
Configure `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and
`STRIPE_LIVE_MODE=False` on the backend only. Never put secrets in React env vars.
Configure a webhook endpoint at `https://BACKEND_HOST/api/stripe/webhook/` for:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`

For local development, use Stripe CLI forwarding to
`localhost:8000/api/stripe/webhook/` and its printed signing secret. Complete a
Stripe test-card checkout, verify the owner email, publish through admin, and
check the resulting job. Also test cancellation, declined payment, and webhook
replay. No real card or charge is needed for acceptance testing.

Before live launch, use the LIVE account key and LIVE endpoint signing secret,
set `STRIPE_LIVE_MODE=True`, and verify the business name, website, customer
support details, receipt settings, and tax treatment in Stripe. The application
charges exactly `JOB_AD_AMOUNT` minor CHF units; it does not add tax automatically.
Do not enable payments until the price/tax presentation is confirmed for the business.

## Existing Render deployment

Update the existing backend and frontend services; do not create duplicate
services or replace their database. Take a database backup before migration.
Inspect the service's linked Git branch, build/start commands, database, and
current environment in Render before changing deployment configuration.

Backend:

- Build: `bash build.sh` (retains the repository's existing migration-at-build
  behavior; on a service supporting pre-deploy commands, move migration and cache
  table creation to pre-deploy for a cleaner release).
- Start: `gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
- Health check: `/api/health/`
- Set `DEBUG=False`, a strong unique `SECRET_KEY`, a durable PostgreSQL
  `DATABASE_URL`, `FRONTEND_URL`, `BACKEND_URL`, and exact `ALLOWED_HOSTS`.
- Set email credentials, `DEFAULT_FROM_EMAIL`, `JOB_REVIEW_EMAIL`, and Stripe
  settings above. Run `python manage.py check --deploy` under these settings.
- Render free web services block SMTP ports 25, 465, and 587. The existing Gmail
  SMTP backend needs a suitable paid service, or replacement with an HTTPS email
  provider. Verify actual email delivery before accepting payments.
- Local SQLite and uploaded media on an ephemeral filesystem are not durable.
  Use PostgreSQL for orders and jobs; configure persistent media storage before
  using uploaded company logos in production.

Frontend:

- Root directory: `financejobs-frontend`
- Build: `npm ci && npm run build`
- Publish directory: `build`
- Set `REACT_APP_API_URL` to the backend origin, with no `/api` suffix.
- Add a rewrite `/*` → `/index.html` so Stripe return URLs and job links work.
- Set security headers: `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin`, and frame protection.

The jobs endpoint now returns `{count, next, previous, results}`. Deploy both
frontend and backend as one coordinated release; the old frontend expects an
array. Keep rollback commits available. The schema changes are additive, but
old and new frontend/API response shapes differ.

Migration 0006 assigns existing jobs `posted_at + 30 days`; stale jobs will be
hidden rather than refreshed artificially. Existing newsletter addresses are
retained but require confirmation before email delivery. They are not contacted
by migrations. Migration does not delete jobs or subscribers.

## Scheduled operations

Configure schedules only after testing on the deployed environment. Example UTC
cron expressions below are suggestions, not provisioned resources:

| Command | Example schedule | Purpose |
| --- | --- | --- |
| `python manage.py retry_notifications` | `*/10 * * * *` | Recover failed paid-ad emails |
| `python manage.py cleanup_expired_jobs --apply` | `0 3 * * *` | Archive expired records |
| `python manage.py refresh_jobs` | `0 4 * * *` | Refresh external job listings |
| `python manage.py send_newsletter --send` | `0 7 * * 1` | Weekly digest for confirmed subscribers |

Cron services need the same database/environment as the backend. Install
Playwright Chromium and OS dependencies in the scraper environment using
`python -m playwright install --with-deps chromium`. Scrapers default to headless;
set `SCRAPER_HEADLESS=False` for local troubleshooting. Test each source with
`python manage.py refresh_jobs --source pictet` (or lgt/ubs/julius/efinancialcareers).
Enable failure alerts for the scheduled service: a zero-result refresh fails
visibly. Imported jobs are refreshed for 30 days from last observation, while
paid listings never get modified or extended by scrapers. Source selectors still
need live verification; unit tests do not verify third-party websites.

Both cleanup and newsletter commands are dry runs unless passed `--apply` or
`--send`. Weekly digests exclude unconfirmed/unsubscribed addresses and record
successful deliveries to avoid duplicates on routine retries. Confirmation links
expire after 24 hours; unsubscribe is an explicit action from the email link.

## Launch verification

Verify HTTPS and admin login; current jobs and filters; missing/expired job pages;
Stripe test success/cancel/decline/replay; email receipt and retry; admin manual
publication and expiry; newsletter confirmation/unsubscribe; deep-link rewrites;
database durability and backup; scheduled refresh and failure alerts. No automated
local test replaces this deployment smoke test.
