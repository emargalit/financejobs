import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
from jobs.models import Job, Company

BASE_URL = "https://juliusbaer.wd3.myworkdayjobs.com"

async def scrape():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(            
            "https://juliusbaer.wd3.myworkdayjobs.com/en-US/External/jobs"
            "?Location_Country=187134fccb084a0ea9b4b95f23890dbe"
            "&jobFamilyGroup=815d7c24d20d01b92609af5514011caf"
            "&jobFamilyGroup=e467d78aa6dc011d4ebed05a7d3d3960"
            "&jobFamilyGroup=e467d78aa6dc012610a5915a7d3d1560"
            "&jobFamilyGroup=e467d78aa6dc01a95ac9bc5a7d3d2d60"
            "&jobFamilyGroup=e3b4d8e50ec910014018bffd61330000"
            "&jobFamilyGroup=e467d78aa6dc01fbd16d985a7d3d1960"
            "&jobFamilyGroup=e467d78aa6dc01dfff28ca5a7d3d3560"
            "&jobFamilyGroup=e467d78aa6dc01034737b95a7d3d2b60"
            "&jobFamilyGroup=e467d78aa6dc012e64bba95a7d3d2360")

        # Accept cookies
        try:
            await page.click('button:has-text("Accept Cookies")')
            print("✅ Cookie banner accepted")
            await page.wait_for_timeout(1000)
        except:
            print("ℹ️ No cookie banner appeared or already dismissed.")

        all_jobs = []

        # Loop through pagination
        while True:
            await page.wait_for_selector('[data-automation-id="jobTitle"]', timeout=10000)
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            job_cards = soup.find_all("a", attrs={"data-automation-id": "jobTitle"})

            for job_link in job_cards:
                try:
                    title = job_link.text.strip()
                    href = job_link["href"]
                    job_url = BASE_URL + href if href.startswith("/") else href

                    location = "Unknown"
                    try:
                        li = job_link.find_parent("li")
                        if li:
                            dt_tags = li.find_all("dt")
                            for dt in dt_tags:
                                if dt.get_text(strip=True).lower() == "locations":
                                    dd = dt.find_next_sibling("dd")
                                    if dd:
                                        location = dd.get_text(strip=True)
                                        break
                    except Exception as e:
                        print(f"⚠️ Failed to extract location: {e}")

                    all_jobs.append({
                        "title": title,
                        "url": job_url,
                        "location": location
                    })
                except Exception as e:
                    print(f"⚠️ Error parsing job card: {e}")

            # Click "next" pagination arrow if available
            try:
                next_button = await page.query_selector('button[aria-label="next"]')
                if next_button and await next_button.is_enabled():
                    await next_button.click()
                    await page.wait_for_timeout(2000)
                else:
                    break
            except:
                break

        print(f"🔍 Found {len(all_jobs)} jobs")

        company_obj, _ = await sync_to_async(Company.objects.get_or_create)(name="Julius Bär")

        for idx, job in enumerate(all_jobs, 1):
            try:
                detail_page = await context.new_page()
                await detail_page.goto(job["url"])
                await detail_page.wait_for_selector('div[data-automation-id="jobPostingDescription"]', timeout=10000)

                html = await detail_page.content()
                soup = BeautifulSoup(html, "html.parser")
                desc_div = soup.select_one('div[data-automation-id="jobPostingDescription"]')

                if desc_div:
                    # Remove inline styles, scripts, unnecessary spans etc.
                    for tag in desc_div.find_all(["style", "script", "svg"]):
                        tag.decompose()
                    for tag in desc_div.find_all(True):
                        tag.attrs = {k: v for k, v in tag.attrs.items() if k in ["class", "href", "src"]}

                    # Optionally: convert to HTML with preserved formatting
                    description = str(desc_div) 
                else:
                    description = "No description available."

                await detail_page.close()

                # Check for duplicates
                exists = await sync_to_async(Job.objects.filter(
                    title=job["title"],
                    location=job["location"],
                    company=company_obj
                ).exists)()

                if not exists:
                    new_job = await sync_to_async(Job.objects.create)(
                        title=job["title"],
                        company=company_obj,
                        location=job["location"],
                        job_type="",
                        salary="",
                        apply_link=job["url"],
                        description=description
                    )
                    print(f"✅ Saved: {new_job.id} {job['title']}")
                else:
                    print(f"⏭ Skipped duplicate: {job['title']}")

            except Exception as e:
                print(f"❌ Error on job {idx}: {e}")

        await browser.close()

class Command(BaseCommand):
    help = "Scrape Julius Bär jobs including descriptions"

    def handle(self, *args, **kwargs):
        asyncio.run(scrape())
