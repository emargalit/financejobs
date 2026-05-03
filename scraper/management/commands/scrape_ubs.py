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
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/90.0.4430.85 Safari/537.36"
            )
        )
        page = await context.new_page()
        search_url = (
            "https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231#keyWordSearch=&locationSearch=Switzerland&Function%20Category=Audit_or_Business%20management,%20administration%20and%20support_or_Client%20advisory%20%2F%20Relationship%20management_or_Compliance_or_Corporate%20services,%20infrastructure%20and%20facilities_or_Equities_or_Finance_or_Fund%20services_or_Management%20and%20Business%20Support_or_Operations_or_Portfolio%20and%20fund%20management_or_Process,%20project%20and%20program%20management_or_Research_or_Risk_or_Sales_or_Sales%20and%20trading_or_Strategy"
        )
        await page.goto(search_url)

        # Accept cookies
        try:
            await page.click('button:has-text("Agree to all")')
            print("✅ Cookie banner accepted")
            await page.wait_for_timeout(1000)
        except:
            print("ℹ️ No cookie banner appeared or already dismissed.")

        await page.wait_for_selector("a.jobProperty.jobtitle", timeout=15000)

        jobs = await page.eval_on_selector_all(
            "a.jobProperty.jobtitle",
            """links => links.map(link => ({
                title: link.innerText.trim(),
                href: link.href
            }))"""
        )

        for idx, job_info in enumerate(jobs[:len(jobs)], start=1):
            try:
                print(f"🔍 Scraping job {idx}: {job_info['title']}")
                await page.goto(job_info["href"])
                await page.wait_for_timeout(1000)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                # ✅ Title fallback
                title_tag = soup.select_one("h1") or soup.select_one("div.jobtitleInJobDetails h2") or soup.find("h2")
                title = title_tag.get_text(strip=True) if title_tag else job_info["title"]

                # ✅ Location via "City" label
                location = "Unknown"
                city_label = soup.find("p", string=lambda text: text and "City" in text)
                if city_label:
                    answer_p = city_label.find_next_sibling("p", class_="answer")
                    if answer_p:
                        location = answer_p.get_text(strip=True)

                # ✅ Scroll to load job detail HTML
                await page.evaluate("""
                    async () => {
                        for (let y = 0, h = document.body.scrollHeight; y < h; y += 400) {
                            window.scrollTo(0, y);
                            await new Promise(r => setTimeout(r, 120));
                        }
                        window.scrollTo(0, document.body.scrollHeight);
                    }
                """)
                await page.wait_for_selector("p.jobDetailTextArea", timeout=10000)

                # ✅ Preserve HTML structure of description
                desc_tags = soup.select("p.jobDetailTextArea")
                description = "\n".join(str(tag) for tag in desc_tags) if desc_tags else "No description."

                company_obj, _ = await sync_to_async(Company.objects.get_or_create)(name="UBS")

                is_duplicate = await sync_to_async(Job.objects.filter(
                    title=title, company=company_obj, location=location
                ).exists)()

                if not is_duplicate:
                    job = await sync_to_async(Job.objects.create)(
                        title=title,
                        company=company_obj,
                        location=location,
                        job_type="",
                        salary="",
                        apply_link=job_info["href"],
                        description=description
                    )
                    print("✅ Saved:", job.id, title)
                else:
                    print("⏭ Skipped duplicate:", title)

                # Go back to job listing page
                await page.goto(search_url)
                await page.wait_for_selector("a.jobProperty.jobtitle", timeout=10000)
                await page.wait_for_timeout(500)

            except Exception as e:
                print(f"❌ Error scraping job {idx}: {e}")

        await browser.close()

class Command(BaseCommand):
    help = "Scrape UBS jobs"

    def handle(self, *args, **kwargs):
        asyncio.run(scrape())
