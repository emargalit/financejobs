import json
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from jobs.models import Company, Job, JobSubmission
from scraper.sources import Listing, SourceError, description_html, parse_dwr, workday, workday_listing
from scraper.persistence import publish_source

FIXTURES = Path(__file__).parent / 'fixtures'


def listing(identifier='job-1', **kwargs):
    return Listing(source='lgt', source_job_id=identifier, title='Investment analyst', location='Zürich', description='<h2>Your role</h2><p>' + 'Research investments and work with the portfolio management team. ' * 4 + '</p>', source_url=f'https://lgt.wd3.myworkdayjobs.com/lgtcurrentvacancies/job/Zurich/{identifier}', **kwargs)


class FeedParserTests(SimpleTestCase):
    def test_real_successfactors_initial_and_next_page_responses(self):
        first = parse_dwr((FIXTURES / 'pictet-initial.txt').read_text())['results']
        second = parse_dwr((FIXTURES / 'pictet-page2.txt').read_text())['results']
        self.assertEqual(first['postingCount'], 56)
        self.assertEqual(len(first['postings']), 10)
        self.assertEqual(second['options']['pagination']['currentPage'], 2)
        self.assertFalse(set(j['id'] for j in first['postings']) & set(j['id'] for j in second['postings']))
        self.assertEqual(first['postings'][0]['title'], 'Data Analytics Expert')
        self.assertEqual(first['postings'][0]['otherValues'][0][0]['shortVal'], 'Switzerland')

    def test_workday_country_and_closed_job_filter(self):
        info = json.loads((FIXTURES / 'workday-detail.json').read_text())
        job = workday_listing('lombard', info)
        self.assertEqual(job.source_job_id, 'R0007743')
        self.assertEqual(job.location, 'Genève')
        self.assertIn('<p>', job.description)
        info['country'] = {'descriptor': 'Luxembourg'}
        self.assertIsNone(workday_listing('lombard', info))
        info['country'] = {'descriptor': 'Switzerland'}
        info['canApply'] = False
        self.assertIsNone(workday_listing('lombard', info))

    def test_workday_total_zero_on_later_pages_still_fetches_every_page(self):
        client = Mock()
        rows = [{'externalPath': f'/job/Zurich/{n}'} for n in range(41)]
        details = json.loads((FIXTURES / 'workday-detail.json').read_text())
        def request(method, url, **kwargs):
            if method == 'POST':
                offset = kwargs['json']['offset']
                return Mock(json=lambda: {'total': 41 if offset == 0 else 0, 'jobPostings': rows[offset:offset + 20]})
            info = deepcopy(details)
            info['jobReqId'] = url.rsplit('/', 1)[-1]
            return Mock(json=lambda: {'jobPostingInfo': info})
        client.request.side_effect = request
        self.assertEqual(len(workday('lombard', client)), 41)
        self.assertEqual([c.kwargs['json']['offset'] for c in client.request.call_args_list if c.args[0] == 'POST'], [0, 20, 40])

    def test_truncated_page_fails_instead_of_archiving_unseen_jobs(self):
        client = Mock()
        client.request.return_value.json.return_value = {'total': 30, 'jobPostings': []}
        with self.assertRaises(SourceError):
            workday('lgt', client)

    def test_description_bullets_and_active_content(self):
        result = description_html('<script>bad()</script><p>• Analyse investments • Manage portfolios</p>')
        self.assertNotIn('bad()', result)
        self.assertEqual(result.count('<li>'), 2)
        intro = description_html('<h2>' + 'Employer introduction. ' * 15 + '</h2><h2>Your role</h2>')
        self.assertTrue(intro.startswith('<p>'))
        self.assertIn('<h2>Your role</h2>', intro)
        self.assertEqual(parse_dwr('var s0={};s0.title="L\\\'investissement";dwr.engine._remoteHandleCallback(\'1\',\'0\',{payload:s0});')['title'], "L'investissement")
        with self.assertRaises(SourceError):
            parse_dwr('<html>Temporarily unavailable</html>')
        with self.assertRaises(SourceError):
            replace(listing(), source_url='https://example.com/apply').validate()


class PublicationTests(TestCase):
    def test_refresh_updates_by_source_id_without_duplicates_and_archives_missing(self):
        publish_source('lgt', [listing(), listing('job-2')])
        original = Job.objects.get(source_job_id='job-1')
        report = publish_source('lgt', [replace(listing(), title='Senior investment analyst')])
        self.assertEqual(report['created'], 0)
        self.assertEqual(report['archived'], 1)
        original.refresh_from_db()
        self.assertEqual(original.title, 'Senior investment analyst')
        self.assertEqual(Job.objects.count(), 2)
        self.assertFalse(Job.objects.get(source_job_id='job-2').is_active)
        self.assertGreater(original.expires_at, timezone.now() + timedelta(days=29))

    def test_invalid_or_empty_batch_does_not_modify_existing_jobs(self):
        publish_source('lgt', [listing()])
        for batch in ([], [replace(listing(), title='Would change'), replace(listing('job-2'), description='broken')], [listing(), listing()]):
            with self.assertRaises(SourceError):
                publish_source('lgt', batch)
        self.assertEqual(Job.objects.get().title, 'Investment analyst')
        self.assertTrue(Job.objects.get().is_active)

    def test_paid_jobs_and_other_sources_are_never_archived_or_modified(self):
        publish_source('lgt', [listing(), listing('job-2')])
        paid = Job.objects.get(source_job_id='job-1')
        JobSubmission.objects.create(title=paid.title, company_name='LGT', contact_email='owner@example.com', location='Zürich', description='Paid', apply_link='https://example.com', job=paid, paid_at=timezone.now())
        other = Job.objects.create(company=Company.objects.create(name='Other bank'), title='Another role', location='Bern', description='Independent', source='other', source_job_id='other-1', apply_link='https://example.com')
        publish_source('lgt', [replace(listing(), title='Must not overwrite')])
        paid.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(paid.title, 'Investment analyst')
        self.assertTrue(paid.is_active)
        self.assertTrue(other.is_active)

    def test_import_is_public_sanitized_and_attributed(self):
        publish_source('lgt', [replace(listing(), description='<img src=x onerror=bad()>' + listing().description)])
        job = Job.objects.get()
        response = self.client.get(f'/api/jobs/{job.pk}/').json()
        self.assertEqual(response['source'], 'lgt')
        self.assertEqual(response['source_url'], listing().source_url)
        self.assertNotIn('onerror', response['description'])
