import asyncio
from urllib.parse import urljoin

from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from jobs.models import Job, Company

BASE_URL = "https://www.lgt.com"
START_URL = "https://www.lgt.com/ch-de/karriere/jobs"

TARGET_LOCATIONS = [
    "Bendern (LI)",
    "Lugano (CH)",
    "Zürich (CH)",
]

ALLOWED_LOCATIONS = {"Bendern", "Lugano", "Zürich"}


def normalize_location_name(location: str) -> str:
    if not location:
        return ""

    location = location.strip()
    replacements = {
        "Bendern (LI)": "Bendern",
        "Lugano (CH)": "Lugano",
        "Zürich (CH)": "Zürich",
        "Zurich (CH)": "Zürich",
        "Bendern": "Bendern",
        "Lugano": "Lugano",
        "Zürich": "Zürich",
        "Zurich": "Zürich",
    }
    return replacements.get(location, location)


def clean_html_fragment(container):
    if not container:
        return "No description available."

    for tag in container.find_all(["script", "style", "svg", "noscript"]):
        tag.decompose()

    soup = BeautifulSoup(str(container), "html.parser")

    blocks = soup.select("div.lgt-intro.lgt-intro--submodule")
    if not blocks:
        return "No description available."

    output_parts = []

    for block in blocks:
        title_span = block.select_one("h2.lgt-intro__title span.lgt-intro__title-block")
        content_div = block.select_one("div.lgt-intro__content div.lgt-rte.lgt-intro__text")

        if not title_span or not content_div:
            continue

        title = " ".join(title_span.get_text(" ", strip=True).split())
        if not title:
            continue

        output_parts.append(
            f'<h3 style="font-weight: 700; font-size: 1.125rem; margin-top: 1rem; margin-bottom: 0.5rem;">{title}</h3>'
        )

        list_open = False

        for child in content_div.children:
            if not getattr(child, "name", None):
                continue

            text = " ".join(child.get_text(" ", strip=True).split())
            if not text:
                continue

            if child.name == "p":
                if list_open:
                    output_parts.append("</ul>")
                    list_open = False
                output_parts.append(f'<p style="margin-bottom: 0.75rem;">{text}</p>')

            elif child.name == "ul":
                if not list_open:
                    output_parts.append(
                        '<ul style="list-style-type: disc; list-style-position: outside; padding-left: 1.5rem; margin-bottom: 0.75rem;">'
                    )
                    list_open = True

                for li in child.find_all("li", recursive=False):
                    li_text = " ".join(li.get_text(" ", strip=True).split())
                    if li_text:
                        output_parts.append(
                            f'<li style="display: list-item; margin-bottom: 0.25rem;">{li_text}</li>'
                        )

            elif child.name == "div":
                nested_ps = child.find_all("p", recursive=False)
                nested_ul = child.find_all("ul", recursive=False)

                if nested_ps:
                    for p in nested_ps:
                        p_text = " ".join(p.get_text(" ", strip=True).split())
                        if p_text:
                            if list_open:
                                output_parts.append("</ul>")
                                list_open = False
                            output_parts.append(f'<p style="margin-bottom: 0.75rem;">{p_text}</p>')

                if nested_ul:
                    if not list_open:
                        output_parts.append(
                            '<ul style="list-style-type: disc; list-style-position: outside; padding-left: 1.5rem; margin-bottom: 0.75rem;">'
                        )
                        list_open = True

                    for ul in nested_ul:
                        for li in ul.find_all("li", recursive=False):
                            li_text = " ".join(li.get_text(" ", strip=True).split())
                            if li_text:
                                output_parts.append(
                                    f'<li style="display: list-item; margin-bottom: 0.25rem;">{li_text}</li>'
                                )

        if list_open:
            output_parts.append("</ul>")

    cleaned = "".join(output_parts).strip()
    return f"<div>{cleaned}</div>" if cleaned else "No description available."


def extract_jobs_from_listing_html(html: str):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    cards = soup.select("div.lgt-teaser--job")
    for card in cards:
        link = card.select_one('a[href^="/ch-de/karriere/jobs/"]')
        if not link:
            continue

        title = link.get_text(" ", strip=True)
        href = link.get("href", "").strip()

        if not title or not href:
            continue

        job_url = urljoin(BASE_URL, href)

        location_items = card.select("ul.lgt-teaser__location li")
        location_values = []

        for li in location_items:
            raw_text = li.get_text(" ", strip=True)
            normalized = normalize_location_name(raw_text)
            if normalized and normalized in ALLOWED_LOCATIONS:
                location_values.append(normalized)

        location_values = list(dict.fromkeys(location_values))
        location = " | ".join(location_values) if location_values else "Unknown"

        jobs.append(
            {
                "title": title,
                "url": job_url,
                "location": location,
            }
        )

    return jobs


async def accept_cookies(page):
    for selector in [
        'button:has-text("Akzeptieren")',
        'button:has-text("Alle akzeptieren")',
        'button:has-text("Accept")',
    ]:
        try:
            await page.click(selector, timeout=3000)
            await page.wait_for_timeout(1000)
            print("✅ Cookie banner handled")
            return
        except Exception:
            pass


async def open_location_filter(page):
    await page.wait_for_selector('button[data-js-lgt-search-filter]', timeout=15000)

    filter_button = page.locator('button[data-js-lgt-search-filter]').filter(
        has=page.locator("span", has_text="Standort")
    ).first

    await filter_button.click()
    await page.wait_for_selector('#search_location[aria-hidden="false"]', timeout=10000)
    await page.wait_for_timeout(500)


async def close_location_filter(page):
    try:
        close_button = page.locator('#search_location button[data-js-flyout-closer]').first
        await close_button.click(timeout=3000)
        await page.wait_for_timeout(500)
    except Exception:
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
        except Exception:
            pass


async def clear_all_location_checkboxes(page):
    await open_location_filter(page)

    checked_boxes = page.locator('#search_location input[type="checkbox"]:checked')
    count = await checked_boxes.count()

    for i in range(count):
        checkbox = checked_boxes.nth(i)
        try:
            await checkbox.uncheck()
            await page.wait_for_timeout(300)
        except Exception:
            checkbox_id = await checkbox.get_attribute("id")
            if checkbox_id:
                label = page.locator(f'#search_location label[for="{checkbox_id}"]').first
                await label.click()
                await page.wait_for_timeout(300)

    await close_location_filter(page)
    await page.wait_for_timeout(1500)


async def select_location(page, location_name: str):
    await clear_all_location_checkboxes(page)
    await open_location_filter(page)

    label = page.locator('#search_location label', has_text=location_name).first
    await label.wait_for(timeout=10000)
    await label.click()
    await page.wait_for_timeout(1000)

    await close_location_filter(page)
    await page.wait_for_timeout(2500)

    print(f"📍 Selected location filter: {location_name}")


async def collect_jobs_for_current_filter(page):
    all_jobs = []
    seen_urls = set()
    visited_pages = set()

    while True:
        current_url = page.url
        if current_url in visited_pages:
            break
        visited_pages.add(current_url)

        await page.wait_for_timeout(1500)
        html = await page.content()
        jobs = extract_jobs_from_listing_html(html)

        new_jobs = 0
        for job in jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
                new_jobs += 1

        print(f"📄 Parsed page: {current_url} -> {new_jobs} new jobs")

        soup = BeautifulSoup(html, "html.parser")

        next_href = None
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            href = a["href"].strip()

            if text == "vor" and "/ch-de/karriere/jobs" in href:
                next_href = urljoin(BASE_URL, href)
                break

        if not next_href or next_href in visited_pages:
            break

        await page.goto(next_href, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1500)

    return all_jobs


async def scrape_job_details(context, company_obj, jobs):
    for idx, job in enumerate(jobs, start=1):
        detail_page = None
        try:
            detail_page = await context.new_page()
            await detail_page.goto(job["url"], wait_until="domcontentloaded", timeout=60000)
            await detail_page.wait_for_timeout(1200)

            html = await detail_page.content()
            soup = BeautifulSoup(html, "html.parser")

            main = soup.find("main") or soup

            h1 = main.find("h1")
            title = h1.get_text(" ", strip=True) if h1 else job["title"]

            location = job["location"]

            if not location or location == "Unknown":
                li_texts = [li.get_text(" ", strip=True) for li in main.find_all("li")]
                possible_locations = []

                for text in li_texts:
                    normalized = normalize_location_name(text)
                    if normalized in ALLOWED_LOCATIONS:
                        possible_locations.append(normalized)

                if possible_locations:
                    location = " | ".join(list(dict.fromkeys(possible_locations)))

            apply_link = job["url"]
            for a in soup.find_all("a", href=True):
                text = a.get_text(" ", strip=True).lower()
                href = a["href"]
                if "bewerben" in text or "apply" in text:
                    apply_link = urljoin(BASE_URL, href)
                    break

            description = clean_html_fragment(main)

            existing_job = await sync_to_async(
                Job.objects.filter(
                    company=company_obj,
                    apply_link=apply_link,
                ).first
            )()

            if existing_job:
                existing_job.title = title
                existing_job.location = location or ""
                existing_job.description = description
                await sync_to_async(existing_job.save)()
                print(f"🔄 Updated: {title} | {location}")
            else:
                new_job = await sync_to_async(Job.objects.create)(
                    title=title,
                    company=company_obj,
                    location=location or "",
                    job_type="",
                    salary="",
                    apply_link=apply_link,
                    description=description,
                )
                print(f"✅ Saved: {new_job.id} {title} | {location}")

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

        company_obj, _ = await sync_to_async(Company.objects.get_or_create)(name="LGT")

        combined_jobs_by_url = {}

        for location_name in TARGET_LOCATIONS:
            await page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(1500)

            await select_location(page, location_name)

            jobs = await collect_jobs_for_current_filter(page)
            selected_normalized = normalize_location_name(location_name)
            print(f"🔍 Found {len(jobs)} jobs for {location_name}")

            for job in jobs:
                job_url = job["url"]

                raw_locations = []
                if job.get("location") and job["location"] != "Unknown":
                    raw_locations = [part.strip() for part in job["location"].split("|") if part.strip()]

                normalized_locations = list(dict.fromkeys(
                    normalize_location_name(loc)
                    for loc in raw_locations
                    if normalize_location_name(loc) in ALLOWED_LOCATIONS
                ))

                if not normalized_locations:
                    print(f"⏭ Skipping {job['title']} because card locations are not in target cities")
                    continue

                if selected_normalized not in normalized_locations:
                    print(
                        f"⏭ Skipping {job['title']} for {selected_normalized} "
                        f"because card locations are {normalized_locations}"
                    )
                    continue

                if job_url not in combined_jobs_by_url:
                    combined_jobs_by_url[job_url] = {
                        "title": job["title"],
                        "url": job_url,
                        "locations": normalized_locations,
                    }
                else:
                    existing = combined_jobs_by_url[job_url]["locations"]
                    combined_jobs_by_url[job_url]["locations"] = list(
                        dict.fromkeys(existing + normalized_locations)
                    )

        combined_jobs = []
        for job in combined_jobs_by_url.values():
            combined_jobs.append(
                {
                    "title": job["title"],
                    "url": job["url"],
                    "location": " | ".join(job["locations"]) if job["locations"] else "Unknown",
                }
            )

        print(f"🔍 Total unique LGT jobs across target locations: {len(combined_jobs)}")

        await scrape_job_details(context, company_obj, combined_jobs)

        await browser.close()


class Command(BaseCommand):
    help = "Scrape LGT jobs for Bendern, Lugano and Zürich only"

    def handle(self, *args, **kwargs):
        asyncio.run(scrape())