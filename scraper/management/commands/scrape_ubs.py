import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from jobs.models import Job, Company
from bs4 import BeautifulSoup

async def scrape():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231#keyWordSearch=&locationSearch=Switzerland&Function%20Category=Audit_or_Business%20management,%20administration%20and%20support_or_Client%20advisory%20%2F%20Relationship%20management_or_Compliance_or_Corporate%20services,%20infrastructure%20and%20facilities_or_Digital_or_Finance_or_Fund%20services_or_Management%20and%20Business%20Support_or_Management%20group_or_Operations_or_Portfolio%20and%20fund%20management_or_Risk_or_Strategy")

        # Accept cookies
        try:
            await page.click('button:has-text("Agree to all")')
            print("✅ Cookie banner accepted")
            await page.wait_for_timeout(1000)
        except:
            print("ℹ️ No cookie banner appeared or already dismissed.")

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Then check for the job list container itself
        await page.wait_for_selector("a.jobProperty.jobtitle", timeout=15000)
        job_links = await page.query_selector_all("a.jobProperty.jobtitle")

        if not job_links:
            print("No job links found after page load.")
            return

        job_links = await page.query_selector_all("a.jobProperty.jobtitle")

        for i in range(min(10, len(job_links))):
            try:
                job_links = await page.query_selector_all("a.jobProperty.jobtitle")
                link = job_links[i]

                href = await link.get_attribute("href")
                if not href:
                    print(f"⚠️ No href on link {i + 1}, skipping.")
                    continue

                apply_link = f"https://jobs.ubs.com{href}"

                print(f"🔍 Scraping job {i + 1}: {apply_link}")
                await link.click(force=True)

                await page.wait_for_selector("div.jobdescriptionInJobDetails", timeout=8000)
                await page.wait_for_timeout(1000)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                title_tag = soup.select_one("div.jobtitleInJobDetails h2")
                title = title_tag.text.strip() if title_tag else "Untitled"

                location_tag = soup.select_one("div.jobtitleInJobDetails ~ div p")
                location = location_tag.text.strip() if location_tag else "Unknown"

                desc_container = soup.select_one("div.jobdescriptionInJobDetails")
                description = desc_container.get_text(separator="\n", strip=True) if desc_container else ""

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
                        apply_link=apply_link,
                        description=description
                    )
                    print("Saved:", job.id, title)
                else:
                    print("⏭ Skipped duplicate:", title)

                await page.go_back()
                await page.wait_for_selector("div.jobtitle a", timeout=10000)
                await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"❌ Failed to scrape job {i + 1}: {e}")

        await browser.close()

class Command(BaseCommand):
    help = "Scrape UBS jobs"

    def handle(self, *args, **kwargs):
        asyncio.run(scrape())
