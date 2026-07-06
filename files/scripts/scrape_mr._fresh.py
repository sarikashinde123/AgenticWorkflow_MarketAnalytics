import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def Mr_Fresh_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto('https://mrfresh.in', wait_until='networkidle')
            await page.wait_for_timeout(random.uniform(1500, 3500))
            pricing = await page.inner_text('selector-for-pricing')
            features = await page.inner_text('selector-for-features')
            homepage_headline = await page.title()
            reviews_summary = await page.inner_text('selector-for-reviews-summary')
            await page.screenshot(path='Mr_Fresh_screenshot.png')
            scrape_status = "success"
        except Exception as e:
            errors = str(e)
            scrape_status = "failed"

        data = {
            "competitor_name": "Mr. Fresh",
            "website": "https://mrfresh.in",
            "scraped_at": str(datetime.now()),
            "scrape_status": scrape_status,
            "pricing": pricing,
            "features": features,
            "homepage_headline": homepage_headline,
            "reviews_summary": reviews_summary,
            "errors": errors
        }
        with open('data/raw/Mr_Fresh_raw.json', 'w') as f:
            json.dump(data, f)
        await browser.close()

asyncio.run(Mr_Fresh_scrape())