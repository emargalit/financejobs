import asyncio
from urllib.parse import urljoin

from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from jobs.models import Job, Company

BASE_URL = "https://career012.successfactors.eu"
START_URL = (
    "https://career012.successfactors.eu/career"
    "?company=banquepict"
    "&career%5fns=job%5flisting%5fsummary"
    "&navBarLevel=JOB%5fSEARCH"
)


def clean_text(text):
    return " ".join((text or "").split()).strip()


def clean_html_fragment(container):
    if not container:
        return "No description available."

    for tag in container.find_all(["script", "style", "svg", "noscript"]):
        tag.decompose()

    output = []

    for elem in container.find_all(["h1", "h2", "h3", "p", "li"]):
        text = clean_text(elem.get_text(" ", strip=True))
        if not text:
            continue

        if elem.name in ["h1", "h2", "h3"]:
            output.append(
                f'<h3 style="font-weight:700;font-size:1.125rem;margin-top:1rem;margin-bottom:0.5rem;">{text}</h3>'
            )

        elif elem.name == "li":
            output.append(
                f'<ul style="list-style-type:disc;padding-left:1.5rem;margin-bottom:0.75rem;">'
                f'<li style="margin-bottom:0.35rem;">{text}</li>'
                f'</ul>'
            )

        else:
            # Fix paragraphs that contain bullet characters like:
            # "• Managing... • Coordinating... • Becoming..."
            if "•" in text:
                parts = [part.strip() for part in text.split("•") if part.strip()]

                if parts:
                    output.append(
                        '<ul style="list-style-type:disc;padding-left:1.5rem;margin-bottom:0.75rem;">'
                    )

                    for part in parts:
                        output.append(
                            f'<li style="margin-bottom:0.35rem;line-height:1.6;">{part}</li>'
                        )

                    output.append("</ul>")
            else:
                output.append(
                    f'<p style="margin-bottom:0.75rem;line-height:1.6;">{text}</p>'
                )

    cleaned = "".join(output).strip()
    return f"<div>{cleaned}</div>" if cleaned else "No description available."


def extract_jobs_from_listing_html(html):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    rows = soup.select("tr.jobResultItem")

    for row in rows:
        title_link = row.select_one("a.jobTitle[href]")
        if not title_link:
            continue

        title = clean_text(title_link.get_text(" ", strip=True))

        if title.lower().startswith("career opportunities"):
            title = title.split(":", 1)[-1].strip()

        href = title_link.get("href", "").strip()
        job_url = urljoin(BASE_URL, href)

        note_items = [
            clean_text(span.get_text(" ", strip=True))
            for span in row.select("div.noteSection span.jobContentEM")
            if clean_text(span.get_text(" ", strip=True))
        ]

        requisition_id = note_items[0] if len(note_items) > 0 else ""
        posted_on = note_items[1] if len(note_items) > 1 else ""
        country = note_items[2] if len(note_items) > 2 else ""
        city = note_items[3] if len(note_items) > 3 else ""

        activity_area = ""
        activity_span = row.select_one("span[id$='_mfield1']")
        if activity_span:
            raw = clean_text(activity_span.get_text(" ", strip=True))
            if not raw.lower().startswith("activity area"):
                activity_area = raw

        location_parts = [part for part in [city, country] if part]
        location = ", ".join(location_parts) if location_parts else "Unknown"

        jobs.append(
            {
                "title": title,
                "url": job_url,
                "location": location,
                "requisition_id": requisition_id,
                "posted_on": posted_on,
                "activity_area": activity_area,
            }
        )

    return jobs

async def accept_cookies(page):
    for selector in [
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        'button:has-text("Alle akzeptieren")',
        'button:has-text("Akzeptieren")',
    ]:
        try:
            await page.click(selector, timeout=3000)
            await page.wait_for_timeout(1000)
            print("✅ Cookie banner handled")
            return
        except Exception:
            pass


async def collect_all_jobs(page):
    all_jobs = []
    seen_urls = set()
    page_number = 1

    while True:
        try:
            await page.wait_for_selector("tr.jobResultItem", timeout=15000)
        except Exception:
            print("⚠️ No Pictet job rows found on this page")
            break

        await page.wait_for_timeout(1200)
        html = await page.content()
        jobs = extract_jobs_from_listing_html(html)
        jobs = [
            job for job in jobs
            if "Switzerland" in job.get("location", "")
        ]

        new_count = 0
        for job in jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
                new_count += 1

        print(f"📄 Parsed Pictet page {page_number} -> {new_count} new jobs")

        next_li = page.locator("li.sfPaginatorArrowContainer.next").first
        next_link = page.locator('a[title="Next Page"]').first

        next_count = await next_link.count()
        if next_count == 0:
            break

        next_li_class = await next_li.get_attribute("class")
        if next_li_class and "disabledArrow" in next_li_class:
            print("✅ Reached last Pictet page")
            break

        first_job_before = None
        if jobs:
            first_job_before = jobs[0]["url"]

        await next_link.click()
        await page.wait_for_timeout(2500)

        if first_job_before:
            try:
                await page.wait_for_function(
                    """(oldUrl) => {
                        const first = document.querySelector('tr.jobResultItem a.jobTitle');
                        return first && first.href !== oldUrl;
                    }""",
                    arg=first_job_before,
                    timeout=10000,
                )
            except Exception:
                pass

        page_number += 1

    return all_jobs


async def scrape_job_details(context, company_obj, jobs):
    for idx, job in enumerate(jobs, start=1):
        detail_page = None

        try:
            detail_page = await context.new_page()
            await detail_page.goto(job["url"], wait_until="domcontentloaded", timeout=60000)
            await detail_page.wait_for_timeout(1500)

            html = await detail_page.content()
            soup = BeautifulSoup(html, "html.parser")

            h1 = soup.find("h1")
            title = clean_text(h1.get_text(" ", strip=True)) if h1 else job["title"]

            if title.lower().startswith("career opportunities"):
                title = title.split(":", 1)[-1].strip()

            description_container = (
                soup.select_one("div.jobContent")
                or soup.select_one("div.jobDescription")
                or soup.select_one("div[class*='job']")
                or soup.find("body")
            )

            description = clean_html_fragment(description_container)

            existing_job = await sync_to_async(
                Job.objects.filter(
                    company=company_obj,
                    apply_link=job["url"],
                ).first
            )()

            if existing_job:
                existing_job.title = title
                existing_job.location = job["location"]
                existing_job.job_type = job["activity_area"] or ""
                existing_job.description = description
                await sync_to_async(existing_job.save)()
                print(f"🔄 Updated: {title} | {job['location']}")
            else:
                new_job = await sync_to_async(Job.objects.create)(
                    title=title,
                    company=company_obj,
                    location=job["location"],
                    job_type=job["activity_area"] or "",
                    salary="",
                    apply_link=job["url"],
                    description=description,
                )
                print(f"✅ Saved: {new_job.id} {title} | {job['location']}")

        except Exception as e:
            print(f"❌ Error on job {idx} ({job.get('title', 'unknown')}): {e}")

        finally:
            if detail_page:
                await detail_page.close()


async def scrape():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
        await accept_cookies(page)

        company_obj, _ = await sync_to_async(Company.objects.get_or_create)(
            name="Pictet"
        )

        jobs = await collect_all_jobs(page)
        print(f"🔍 Found {len(jobs)} Pictet jobs")

        await scrape_job_details(context, company_obj, jobs)

        await browser.close()


class Command(BaseCommand):
    help = "Scrape Pictet jobs from SuccessFactors"

    def handle(self, *args, **kwargs):
        asyncio.run(scrape())