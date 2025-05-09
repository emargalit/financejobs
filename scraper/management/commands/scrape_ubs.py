import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from jobs.models import Job, Company
from bs4 import BeautifulSoup

async def scrape():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36"
        )
        page = await context.new_page()

        await page.goto("https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231#keyWordSearch=&locationSearch=Switzerland&Job%20Type=Temporary%20%2F%20Contract")

        try:
            await page.click('button:has-text("Agree to all")')
            print("✅ Cookie banner accepted")
            await page.wait_for_timeout(1000)
        except:
            print("ℹ️ No cookie banner appeared or already dismissed.")

        await page.wait_for_selector("a.jobProperty.jobtitle", timeout=15000)

        for i in range(10):
            try:
                # 🔁 Re-fetch job links each time
                job_links = await page.query_selector_all("a.jobProperty.jobtitle")
                if i >= len(job_links):
                    print(f"⚠️ Index {i} out of bounds — only found {len(job_links)} job links.")
                    break

                link = job_links[i]
                job_title_text = await link.inner_text()
                print(f"🔍 Scraping job {i + 1}: {job_title_text}")
                await link.click(force=True)

                await page.wait_for_selector("div.jobDetailsMainDiv", timeout=10000)
                await page.wait_for_timeout(1000)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                title_tag = soup.select_one("h1") or soup.select_one("div.jobtitleInJobDetails h2") or soup.find("h2")
                title = title_tag.text.strip() if title_tag else job_title_text  # fallback to job list title

                location_tag = soup.select_one("div.jobtitleInJobDetails ~ div p")
                location = location_tag.text.strip() if location_tag else "Unknown"

                # ✅ Adjusted selector for UBS job descriptions
                description_parts = soup.select("p.oQ\\:ClassName, p[class*='jobdescriptionInJobDetails']")
                description = "\n".join(p.get_text(strip=True) for p in description_parts) if description_parts else "No description."

                company_obj, _ = await sync_to_async(Company.objects.get_or_create)(name="UBS")
                job_exists = await sync_to_async(Job.objects.filter(
                    title=title, company=company_obj, location=location
                ).exists)()

                if not job_exists:
                    job = await sync_to_async(Job.objects.create)(
                        title=title,
                        company=company_obj,
                        location=location,
                        job_type="",
                        salary="",
                        apply_link="https://jobs.ubs.com",  # Use original apply_link if needed
                        description=description
                    )
                    print("✅ Saved:", job.id, title)
                else:
                    print("⏭ Skipped duplicate:", title)

                # ⬅️ Go back and wait
                await page.go_back()
                await page.wait_for_selector("a.jobProperty.jobtitle", timeout=10000)
                await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"❌ Failed to scrape job {i + 1}: {e}")

        await browser.close()

class Command(BaseCommand):
    help = "Scrape UBS jobs"

    def handle(self, *args, **kwargs):
        asyncio.run(scrape())
