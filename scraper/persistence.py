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


def publish_source(source, listings):
    """Publish one complete validated feed atomically; never modify paid adverts."""
    from datetime import date
    from django.db import transaction
    from jobs.models import Company
    from .sources import SOURCES, SourceError

    if not listings:
        raise SourceError('Refusing to publish an empty feed')
    identifiers = set()
    for listing in listings:
        listing.validate()
        if listing.source != source or listing.source_job_id in identifiers:
            raise SourceError('Mismatched source or duplicate source job ID')
        identifiers.add(listing.source_job_id)
    created = updated = protected = 0
    with transaction.atomic():
        company, _ = Company.objects.get_or_create(name=SOURCES[source][0], defaults={'company_type': 'Financial institution'})
        # Serialize concurrent imports for this institution.
        Company.objects.select_for_update().get(pk=company.pk)
        for listing in listings:
            job = Job.objects.filter(source=source, source_job_id=listing.source_job_id).first()
            if job is None:
                job = Job.objects.filter(company=company, source='', jobsubmission__isnull=True, apply_link=listing.source_url).first()
            if job is None:
                job = Job.objects.filter(company=company, source='', jobsubmission__isnull=True, title=listing.title, location=listing.location).first()
            if job is not None and hasattr(job, 'jobsubmission'):
                protected += 1
                continue
            if job is None:
                job = Job(company=company)
                created += 1
            else:
                updated += 1
            for field in ('source', 'source_job_id', 'title', 'location', 'description', 'source_url', 'job_type', 'work_schedule'):
                setattr(job, field, getattr(listing, field))
            job.source_posted_at = date.fromisoformat(listing.source_posted_at) if listing.source_posted_at else None
            job.apply_link = listing.source_url
            job.is_active = True
            job.last_seen_at = timezone.now()
            job.expires_at = listing_expiry()
            job.save()
        archived = Job.objects.filter(source=source, is_active=True, jobsubmission__isnull=True).exclude(source_job_id__in=identifiers).update(is_active=False)
    return {'created': created, 'updated': updated, 'archived': archived, 'protected': protected, 'total': len(listings)}
