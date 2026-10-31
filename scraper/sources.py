"""Public employer careers feeds. No applicant credentials or browser required."""
import html
import json
import re
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import date, datetime
from urllib.parse import quote, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

SOURCES = {
    'lgt': ('LGT', 'lgt', 'lgtcurrentvacancies'),
    'julius': ('Julius Bär', 'juliusbaer', 'External'),
    'vontobel': ('Vontobel', 'vontobel', 'Vontobel_External_Career'),
    'lombard': ('Lombard Odier', 'lombardodier', 'Lombard_Odier_Careers'),
    'pictet': ('Pictet', None, None),
}
SWISS_COUNTRY_ID = '187134fccb084a0ea9b4b95f23890dbe'
CITY_NAMES = {'Zurich': 'Zürich', 'Geneva': 'Genève', 'Geneve': 'Genève', 'Berne': 'Bern'}


class SourceError(Exception):
    pass


def text(value):
    return ' '.join(BeautifulSoup(str(value or ''), 'html.parser').get_text(' ', strip=True).split())


def location_name(value):
    value = text(value)
    # Workday includes the street after " / " on some boards.
    value = value.split('/')[0].strip()
    return CITY_NAMES.get(value, value)


def job_type(title, explicit=''):
    label = (title + ' ' + explicit).lower()
    if re.search(r'intern|graduate|trainee|apprenti|lehrstelle|praktik|stage\b|stagiaire', label):
        return 'Internships / Graduate Programs'
    if re.search(r'fixed.term|temporary|befrist|contract|contrat|cdd\b', label):
        return 'Fixed-Term / Contract'
    if re.search(r'part.time|teilzeit', label):
        return 'Part-Time'
    if re.search(r'regular|permanent|unbefrist|festanstellung', label):
        return 'Permanent'
    return ''


def description_html(value):
    soup = BeautifulSoup(value or '', 'html.parser')
    for node in soup(['script', 'style', 'iframe', 'form', 'button', 'svg', 'noscript']):
        node.decompose()
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        if len(heading.get_text(' ', strip=True)) > 180:
            heading.name = 'p'
        elif heading.name in ('h1', 'h5', 'h6'):
            heading.name = 'h3'
    # SuccessFactors commonly stores bullets inside a single paragraph.
    for p in list(soup.find_all('p')):
        plain = p.get_text(' ', strip=True)
        if plain.count('•') >= 2:
            parts = plain.split('•')
            fragment = BeautifulSoup(''.join((f'<p>{html.escape(parts[0])}</p>' if parts[0].strip() else '', '<ul>', *[f'<li>{html.escape(x.strip())}</li>' for x in parts[1:] if x.strip()], '</ul>')), 'html.parser')
            p.replace_with(fragment)
    return str(soup)


@dataclass
class Listing:
    source: str
    source_job_id: str
    title: str
    location: str
    description: str
    source_url: str
    job_type: str = ''
    work_schedule: str = ''
    source_posted_at: str | None = None

    def validate(self):
        if self.source not in SOURCES or not self.source_job_id or not self.title or not self.location:
            raise SourceError('Missing source ID, title or Swiss location')
        if len(text(self.description)) < 100:
            raise SourceError(f'{self.source}/{self.source_job_id}: incomplete description')
        expected = 'career012.successfactors.eu' if self.source == 'pictet' else f'{SOURCES[self.source][1]}.wd3.myworkdayjobs.com'
        parsed = urlsplit(self.source_url)
        if parsed.scheme != 'https' or parsed.hostname != expected:
            raise SourceError('Application URL does not belong to the employer careers site')
        for key, limit in [('title', 255), ('location', 255), ('source_job_id', 150), ('source_url', 500), ('work_schedule', 100)]:
            if len(getattr(self, key)) > limit:
                raise SourceError(f'{key} exceeds storage limit')
        if self.source_posted_at:
            date.fromisoformat(self.source_posted_at)
        return self


class PublicClient:
    def __init__(self):
        self.client = httpx.Client(timeout=30, follow_redirects=True, headers={'User-Agent': 'SwissFinanceJobs/1.0 (+https://swissfinancejobs.ch)', 'Accept-Language': 'en-US,en;q=0.9'})

    def request(self, method, url, **kwargs):
        for attempt in range(3):
            time.sleep(.15 if attempt == 0 else 2 ** attempt)
            try:
                response = self.client.request(method, url, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as error:
                if isinstance(error, httpx.HTTPStatusError) and error.response.status_code not in (429, 500, 502, 503, 504):
                    raise SourceError(f'Careers feed returned HTTP {error.response.status_code}') from error
                if attempt == 2:
                    raise SourceError(f'Careers feed unavailable: {type(error).__name__}') from error

    def close(self):
        self.client.close()


def workday_listing(source, info):
    country = info.get('country', {})
    if country.get('descriptor') != 'Switzerland' and country.get('id') != SWISS_COUNTRY_ID:
        return None
    if info.get('canApply') is False or info.get('posted') is False:
        return None
    location = location_name(info.get('location'))
    if not location or re.fullmatch(r'\d+ Locations', location):
        raise SourceError('Missing detailed Swiss location')
    title = text(info['title'])
    return Listing(source=source, source_job_id=info['jobReqId'], title=title,
        location=location, description=description_html(info.get('jobDescription')),
        source_url=info['externalUrl'], work_schedule=text(info.get('timeType')),
        job_type=job_type(title, str(info.get('jobType', '')) + ' ' + str(info.get('timeType', ''))),
        source_posted_at=info.get('startDate', '')[:10] or None).validate()


def workday(source, client):
    _, tenant, site = SOURCES[source]
    base = f'https://{tenant}.wd3.myworkdayjobs.com/wday/cxs/{tenant}/{site}'
    offset, total, seen, result = 0, None, set(), []
    while total is None or offset < total:
        data = client.request('POST', base + '/jobs', json={'appliedFacets': {}, 'limit': 20, 'offset': offset, 'searchText': ''}).json()
        # Workday sends total=0 on subsequent pages even when jobs remain.
        if total is None:
            total = data['total']
        if not isinstance(total, int) or total < 0 or total > 5000:
            raise SourceError('Unexpected careers feed total')
        rows = data['jobPostings']
        if not rows and offset < total:
            raise SourceError('Pagination ended before all jobs were returned')
        for row in rows:
            path = row['externalPath']
            if path in seen:
                raise SourceError('Careers pagination repeated a job')
            seen.add(path)
            if not path.startswith('/job/') or '..' in path:
                raise SourceError('Unexpected job detail path')
            info = client.request('GET', base + path).json()['jobPostingInfo']
            listing = workday_listing(source, info)
            if listing:
                result.append(listing)
        offset += len(rows)
    # A zero-result response might be a changed page or a temporary upstream issue.
    if not result:
        raise SourceError('No validated Swiss jobs returned; existing listings retained')
    return result


def parse_dwr(response):
    """Decode DWR's object assignments as data, never execute remote JavaScript."""
    objects = {name: ([] if kind == '[]' else {}) for name, kind in re.findall(r'var (s\d+)=(\{\}|\[\]);', response)}
    value_pattern = r'(?:"(?:\\.|[^"\\])*"|s\d+|true|false|null|-?\d+(?:\.\d+)?)'
    assignments = re.finditer(r'(s\d+)(?:\.([A-Za-z_][\w]*)|\[(\d+)\])=(' + value_pattern + r');', response)
    for match in assignments:
        name, key, index, raw = match.groups()
        # DWR escapes apostrophes in double-quoted strings (valid JS, not JSON).
        raw_json = re.sub(r'\\(?:x[0-9a-fA-F]{2}|.)', lambda m: "'" if m[0] == "\\'" else ('\\u00' + m[0][2:] if m[0].startswith('\\x') else m[0]), raw)
        value = objects[raw] if raw in objects else json.loads(raw_json)
        target = objects[name]
        if index is not None:
            index = int(index)
            if index > 10000:
                raise SourceError('Invalid DWR array index')
            while len(target) <= index:
                target.append(None)
            target[index] = value
        else:
            target[key] = value
    callback = re.search(r"_remoteHandleCallback\('[^']+','[^']+',\{([\w:,]+)\}\)", response)
    if not callback:
        raise SourceError('Unrecognized public careers response')
    result = {key: objects[ref] for key, ref in (part.split(':') for part in callback.group(1).split(','))}
    return result.get('payload', result)


class PictetFeed:
    base = 'https://career012.successfactors.eu'
    page_path = '/career?company=banquepict&career_ns=job_listing_summary&navBarLevel=JOB_SEARCH'

    def __init__(self, client):
        self.client, self.batch = client, 0
        page = client.request('GET', self.base + self.page_path).text
        token = re.search(r'var ajaxSecKey="([^"]+)"', page)
        if not token:
            raise SourceError('Pictet public careers token missing')
        self.headers = {'Content-Type': 'text/plain', 'viewId': '/ui/rcmcareer/pages/careersite/career.jsp.xhtml', 'x-ajax-token': token.group(1), 'Origin': self.base, 'Referer': self.base + self.page_path}
        self.session_id = uuid.uuid4().hex

    def call(self, method, value):
        fields = {'callCount': '1', 'page': self.page_path, 'httpSessionId': '', 'scriptSessionId': self.session_id,
                  'c0-scriptName': 'careerJobSearchControllerProxy', 'c0-methodName': method, 'c0-id': '0', 'batchId': str(self.batch)}
        counter = 0
        def encode(value, name):
            nonlocal counter
            if isinstance(value, dict):
                refs = []
                for key, child in value.items():
                    counter += 1
                    child_name = f'c0-e{counter}'
                    encode(child, child_name)
                    refs.append(key + ':reference:' + child_name)
                fields[name] = 'Object_Object:{' + ', '.join(refs) + '}'
            elif isinstance(value, bool):
                fields[name] = 'boolean:' + str(value).lower()
            elif isinstance(value, int):
                fields[name] = 'number:' + str(value)
            else:
                fields[name] = 'string:' + quote(str(value), safe='')
        encode(value, 'c0-param0')
        body = '\n'.join(k + '=' + v for k, v in fields.items()) + '\n'
        response = self.client.request('POST', f'{self.base}/xi/ajax/remoting/call/plaincall/careerJobSearchControllerProxy.{method}.dwr', headers=self.headers, content=body)
        self.batch += 1
        return parse_dwr(response.text)

    def listings(self):
        payload = self.call('getInitialJobSearchData', {'filterOnly': '', 'jobAlertId': '', 'returnToList': '', 'browserTimeZone': 'Europe/Zurich'})
        results = payload['results']
        seen, listings = set(), []
        for _ in range(100):
            postings = results['postings']
            if not postings:
                raise SourceError('Pictet returned an empty page')
            for posting in postings:
                identifier = str(posting['id'])
                if identifier in seen:
                    raise SourceError('Pictet pagination repeated a job')
                seen.add(identifier)
                fields = {field['fieldId']: field['shortVal'] for group in posting['otherValues'] for field in group}
                if fields.get('filter1') != 'Switzerland':
                    continue
                url = f'{self.base}/career?career_ns=job_listing&company=banquepict&career_job_req_id={identifier}&rcm_site_locale=en_GB'
                detail = BeautifulSoup(self.client.request('GET', url).text, 'html.parser')
                blocks = detail.select('.joqReqDescription')
                if not blocks:
                    raise SourceError(f'Pictet {identifier}: description missing')
                title = text(posting['title'])
                listings.append(Listing(source='pictet', source_job_id=identifier, title=title,
                    location=location_name(fields.get('filter2')), description=description_html(''.join(str(b) for b in blocks)),
                    source_url=url, job_type=job_type(title, fields.get('filter3', '')),
                    source_posted_at=datetime.strptime(posting['postingDate'], '%d/%m/%Y').date().isoformat()).validate())
            options = results['options']
            pagination = options['pagination']
            if len(seen) >= results['postingCount']:
                break
            pagination['currentPage'] += 1
            results = self.call('search', options)
            if 'results' in results:
                results = results['results']
        else:
            raise SourceError('Pictet pagination exceeded safety limit')
        if not listings:
            raise SourceError('No Swiss Pictet jobs returned; existing listings retained')
        return listings


def collect(source):
    client = PublicClient()
    try:
        return PictetFeed(client).listings() if source == 'pictet' else workday(source, client)
    finally:
        client.close()
