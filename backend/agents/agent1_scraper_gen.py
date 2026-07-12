"""
Agent 1 — Scraper Generator
Pass-through: converts Agent 0's competitor list into scraper instructions
without an API call. Agent 2 scrapes directly by competitor name.
"""
from __future__ import annotations


def run(input_schema: dict, on_token=None, on_usage=None, model: str | None = None) -> list[dict]:
    """
    Converts competitors from input_schema into scraper instruction dicts.
    No LLM call — pure data transformation.
    """
    competitors = input_schema.get("competitors", [])
    business = input_schema.get("business", {})
    btype = business.get("type", "")

    scripts = []
    for c in competitors:
        name = c.get("name", "Unknown")
        website = c.get("website", "")
        scripts.append({
            "competitor_name": name,
            "website": website,
            "search_queries": [
                f"{name} {btype} pricing services reviews",
            ],
            "target_data": ["pricing", "services", "reviews", "contact", "hours"],
            "priority": c.get("priority", "medium"),
        })

    if on_token:
        on_token(f"Generated {len(scripts)} scraper scripts (pass-through)")

    return scripts
