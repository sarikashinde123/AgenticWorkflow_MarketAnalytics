"""
Agent 2 — Website Scraper
Model  : claude-haiku-4-5-20251001
Tool   : web_search (Claude native)
Output : raw_data.json — competitor data per competitor
"""
from __future__ import annotations
import json
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-haiku-4-5-20251001"
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}

SYSTEM = """
You are Agent 2 — the Website Scraper in a competitive intelligence pipeline.

Given scrape instructions for a competitor, use web_search to gather:
- Pricing / rates
- Services offered
- Customer reviews and ratings
- Business hours and contact info
- Unique selling points and messaging
- SEO keywords and content themes

Return a structured JSON with these exact keys:
{
  "competitor_name": "...",
  "website": "...",
  "scraped_at": "ISO timestamp",
  "scrape_status": "success|partial|failed",
  "pricing": {},
  "services": [],
  "reviews_summary": {"rating": 0.0, "count": 0, "highlights": []},
  "business_hours": "",
  "contact": {},
  "homepage_headline": "",
  "usps": [],
  "seo_keywords": [],
  "errors": []
}

Return ONLY the JSON — no markdown, no explanation.
"""


def _scrape_one(competitor: dict, on_token=None, on_usage=None) -> dict:
    name = competitor.get("competitor_name", "Unknown")
    website = competitor.get("website", "")
    queries = competitor.get("search_queries", [f"{name} pricing services reviews"])

    prompt = (
        f"Competitor: {name}\n"
        f"Website: {website}\n"
        f"Search queries to run:\n"
        + "\n".join(f"- {q}" for q in queries)
        + "\n\nScrape all available data using web_search and return the structured JSON."
    )

    messages = [{"role": "user", "content": prompt}]
    full_text = ""

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        )
        if on_usage:
            on_usage(response.usage)

        for block in response.content:
            if hasattr(block, "text"):
                full_text += block.text
                if on_token:
                    on_token(block.text)

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Search executed.",
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    try:
        clean = full_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except json.JSONDecodeError:
        return {
            "competitor_name": name, "website": website,
            "scrape_status": "failed", "errors": ["JSON parse error"],
            "pricing": {}, "services": [], "reviews_summary": {},
            "homepage_headline": "", "usps": [], "seo_keywords": []
        }


def run(scraper_scripts: list[dict], on_token=None, on_usage=None) -> list[dict]:
    """
    Runs Agent 2 for each competitor in scraper_scripts.
    Returns a list of raw competitor data dicts.
    """
    results = []
    for script in scraper_scripts:
        name = script.get("competitor_name", "?")
        if on_token:
            on_token(f"\n[Scraping {name}...]\n")
        data = _scrape_one(script, on_token=on_token, on_usage=on_usage)
        results.append(data)
    return results
