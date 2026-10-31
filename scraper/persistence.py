from django.utils import timezone
from jobs.models import Job, listing_expiry


def refresh_scraped_job(*, company, title, location, description, apply_link, job_type='', salary=''):
    # Paid listings are never changed or extended by a scraper.
    job = Job.objects.filter(company=company, apply_link=apply_link).first()
    if job is None:
        job = Job.objects.filter(company=company, title=title, location=location).first()
    if job is not None and hasattr(job, 'jobsubmission'):
        return job
    if job is None:
        job = Job(company=company)
    job.title, job.location, job.description = title, location, description
    job.apply_link, job.job_type, job.salary = apply_link, job_type, salary
    job.last_seen_at = timezone.now()
    job.expires_at = listing_expiry()
    job.is_active = True
    job.save()
    return job
