import asyncio
from playwright.async_api import async_playwright
import json
import random
import time
from datetime import datetime

async def scrape_razorpay():
    result = {
        "competitor_name": "Razorpay",
        "website": "https://razorpay.com",
        "scraped_at": datetime.utcnow().isoformat(),
        "scrape_status": "success",
        "pricing": None,
        "features": None,
        "homepage_headline": None,
        "homepage_usp": None,
        "reviews_summary": None,
        "blog_topics": None,
        "job_postings": None,
        "errors": None
    }
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto("https://razorpay.com", wait_until='networkidle')
            await asyncio.sleep(random.uniform(1.5, 3.5))
            result["homepage_headline"] = await page.title()
            result["homepage_usp"] = await page.inner_text(".usp-selector")

        except Exception as e:
            errors.append(f"Homepage scraping error: {str(e)}")

        try:
            await page.goto("https://razorpay.com/pricing", wait_until='networkidle')
            await asyncio.sleep(random.uniform(1.5, 3.5))
            result["pricing"] = await page.inner_text("#pricing")

        except Exception as e:
            errors.append(f"Pricing scraping error: {str(e)}")

        try:
            await page.goto("https://razorpay.com/features", wait_until='networkidle')
            await asyncio.sleep(random.uniform(1.5, 3.5))
            result["features"] = await page.inner_text("#features")

        except Exception as e:
            errors.append(f"Features scraping error: {str(e)}")

        try:
            await page.goto("https://razorpay.com/resources/blog", wait_until='networkidle')
            await asyncio.sleep(random.uniform(1.5, 3.5))
            result["blog_topics"] = await page.inner_text(".blog-topics")

        except Exception as e:
            errors.append(f"Blog scraping error: {str(e)}")

        try:
            await page.goto("https://razorpay.com/reviews", wait_until='networkidle')
            await asyncio.sleep(random.uniform(1.5, 3.5))
            result["reviews_summary"] = await page.inner_text(".reviews-summary")

        except Exception as e:
            errors.append(f"Reviews scraping error: {str(e)}")

        try:
            await page.goto("https://razorpay.com/careers", wait_until='networkidle')
            await asyncio.sleep(random.uniform(1.5, 3.5))
            result["job_postings"] = await page.inner_text(".job-postings")

        except Exception as e:
            errors.append(f"Jobs scraping error: {str(e)}")

        result["errors"] = errors
        await page.screenshot(path="razorpay_screenshot.png")

        with open("data/raw/razorpay_raw.json", "w") as f:
            json.dump(result, f, indent=4)

        await browser.close()

asyncio.run(scrape_razorpay())