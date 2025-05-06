import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from jobs.models import Job
from bs4 import BeautifulSoup

async def scrape():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale='en-US'
        )
        page = await context.new_page()
        await page.goto(
            'https://www.efinancialcareers.ch/jobs?countryCode=CH&radius=40&radiusUnit=km&pageSize=15&filters.sectors=PRIVATE_BANKING_WEALTH_MANAGEMENT%7CINVESTMENT_BANKING_M_A%7CPRIVATE_EQUITY_VENTURE_CAPITAL%7CTRADING%7CHEDGE_FUNDS%7CINVESTMENT_CONSULTING%7CQUANTITATIVE_ANALYTICS%7CCAPITAL_MARKETS%7CCREDIT%7CGRADUATES_INTERNSHIPS%7CINVESTOR_RELATIONS_PR%7CEQUITIES%7CACCOUNTING_FINANCE%7CASSET_MANAGEMENT%7CRISK_MANAGEMENT%7CRETAIL_BANKING%7CCORPORATE_BANKING&currencyCode=CHF&language=de&includeUnspecifiedSalary=true'
        )
        await page.wait_for_selector('div.title h3')

        for i in range(19):
            try:
                show_more_button = await page.query_selector('button:has-text("Mehr anzeigen")')
                if show_more_button:
                    await show_more_button.click()
                    print(f"Clicked 'Mehr anzeigen' ({i + 1}/19)")
                    await page.wait_for_timeout(2000)  
                else:
                    print("No more 'Mehr anzeigen' button found.")
                    break
            except Exception as e:
                print(f"Failed to click 'Mehr anzeigen' on attempt {i + 1}:", e)
                break

        await page.mouse.wheel(0, 2000)
        await page.wait_for_timeout(3000)

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        job_cards = soup.select('div.title')

        for job_div in job_cards:
            print("Found a job card!")
            a_tag = job_div.find('a')
            if not a_tag:
                print("Skipping job because no <a> inside!")
                continue

            title_tag = job_div.find('h3')
            title = title_tag.text.strip() if title_tag else 'No Title'
            apply_link = a_tag['href']

            company_div = job_div.find_next('div', class_='font-body-3 company col ng-star-inserted')
            company = company_div.text.strip() if company_div else 'Unknown Company'

            location_div = job_div.find_next('div', class_='font-helper-text location col ng-star-inserted')
            location_spans = location_div.find_all('span') if location_div else []

            location = location_spans[0].text.strip() if len(location_spans) > 0 else 'Unknown Location'
            job_type = location_spans[1].text.strip() if len(location_spans) > 1 else ""

            try:
                job, created = await sync_to_async(Job.objects.get_or_create)(
                    title=title,
                    company_name=company,
                    location=location,
                    defaults={
                        "job_type": job_type,
                        "salary": "",
                        "apply_link": apply_link,
                        "description": "Scraped from eFinancialCareers.ch"
                    }
                )
                if created:
                    print("Saved:", job.id, job.title)
                else:
                    print("Skipped (duplicate):", job.title)
            except Exception as e:
                print("Failed to save job:", e)

        await browser.close()

class Command(BaseCommand):
    help = 'Scrape finance jobs from eFinancialCareers.ch'

    def handle(self, *args, **kwargs):
        print("Starting browser...")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(scrape())
