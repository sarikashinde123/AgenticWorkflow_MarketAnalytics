"""
Agent 2 — Website Scraper
Model  : claude-haiku-4-5-20251001
Tool   : web_search (Claude native)
Output : raw_data.json — competitor data per competitor

Scrapes competitors in parallel (ThreadPoolExecutor).
Caches scraped data per competitor in PostgreSQL (7-day TTL).
"""
from __future__ import annotations
import json
import hashlib
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-haiku-4-5-20251001"
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}

SYSTEM = """
You are Agent 2 — the Website Scraper in a competitive intelligence pipeline.

Given scrape instructions for MULTIPLE competitors, use web_search to gather data
for ALL of them in a single session. For each competitor, collect:
- Pricing / rates
- Services offered
- Customer reviews and ratings
- Business hours and contact info
- Unique selling points and messaging

Return a JSON ARRAY — one object per competitor, each with these exact keys:
[
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
]

Return ONLY the JSON array — no markdown, no explanation.
"""


def _extract_json(text: str) -> dict | list | None:
    """Try multiple strategies to extract JSON from model output."""
    clean = text.strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    if "```" in clean:
        parts = clean.split("```")
        for part in parts:
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{") or p.startswith("["):
                try:
                    return json.loads(p)
                except json.JSONDecodeError:
                    pass
    # Try outermost array
    bracket_start = clean.find("[")
    if bracket_start >= 0:
        depth = 0
        for i in range(bracket_start, len(clean)):
            if clean[i] == "[":
                depth += 1
            elif clean[i] == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(clean[bracket_start : i + 1])
                    except json.JSONDecodeError:
                        break
    # Try outermost object (single competitor fallback)
    brace_start = clean.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(clean)):
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(clean[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _scrape_one(comp: dict, on_token=None, on_usage=None, use_model: str | None = None) -> dict:
    """Scrape a single competitor via web_search."""
    name = comp.get("competitor_name", "Unknown")
    website = comp.get("website", "")
    print(f"[Agent2] Scraping: {name}")

    prompt = (
        f"Research this competitor and return a JSON object.\n\n"
        f"Competitor: {name}\n"
        f"Website: {website}\n\n"
        f"Run web_search for \"{name} pricing membership fees reviews\" — "
        f"focus on finding ACTUAL PRICES (monthly/annual fees, membership plans). "
        f"Check JustDial, Google Maps, and gym listing sites for pricing. "
        f"Then return the JSON."
    )

    messages = [{"role": "user", "content": prompt}]
    full_text = ""

    for _ in range(3):
        response = client.messages.create(
            model=use_model or MODEL,
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

    parsed = _extract_json(full_text)

    if isinstance(parsed, list) and parsed:
        parsed = parsed[0]
    if isinstance(parsed, dict):
        parsed.setdefault("competitor_name", name)
        parsed.setdefault("website", website)
        print(f"[Agent2]   {name}: status={parsed.get('scrape_status', '?')}, "
              f"services={len(parsed.get('services', []))}")
        return parsed

    print(f"[Agent2]   {name}: parse FAILED")
    return {
        "competitor_name": name, "website": website,
        "scrape_status": "failed", "errors": ["JSON parse error"],
        "pricing": {}, "services": [], "reviews_summary": {},
        "homepage_headline": "", "usps": [], "seo_keywords": []
    }


CACHE_TTL_DAYS = 7


def _cache_key(name: str, website: str) -> str:
    raw = f"{name.strip().lower()}|{website.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_cached(scripts: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (cached_results, uncached_scripts)."""
    from db.database import SessionLocal, CompetitorCache
    cached = []
    uncached = []
    cutoff = datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)
    db = SessionLocal()
    try:
        for s in scripts:
            key = _cache_key(s.get("competitor_name", ""), s.get("website", ""))
            row = db.query(CompetitorCache).filter(
                CompetitorCache.cache_key == key,
                CompetitorCache.created_at >= cutoff,
            ).first()
            if row:
                print(f"[Agent2] CACHE HIT: {s.get('competitor_name')}")
                cached.append(row.scraped_data)
            else:
                uncached.append(s)
    finally:
        db.close()
    return cached, uncached


def _store_cache(scripts: list[dict], results: list[dict]):
    """Store scraped results in the cache."""
    from db.database import SessionLocal, CompetitorCache
    db = SessionLocal()
    try:
        for script, result in zip(scripts, results):
            if result.get("scrape_status") == "failed":
                continue
            key = _cache_key(script.get("competitor_name", ""), script.get("website", ""))
            existing = db.query(CompetitorCache).filter_by(cache_key=key).first()
            if existing:
                existing.scraped_data = result
                existing.created_at = datetime.utcnow()
            else:
                db.add(CompetitorCache(
                    cache_key=key,
                    competitor_name=script.get("competitor_name", ""),
                    website=script.get("website", ""),
                    scraped_data=result,
                ))
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Agent2] Cache write error: {e}")
    finally:
        db.close()


MAX_PARALLEL = 6


def run(scraper_scripts: list[dict], on_token=None, on_usage=None, model: str | None = None) -> list[dict]:
    """
    Scrapes competitors in parallel (one thread each).
    Checks cache first — only scrapes competitors not already cached.
    """
    cached_results, uncached_scripts = _get_cached(scraper_scripts)
    print(f"[Agent2] Cache: {len(cached_results)} hits, {len(uncached_scripts)} misses")

    if on_token and cached_results:
        names = [r.get("competitor_name", "?") for r in cached_results]
        on_token(f"\n[Using cached data for: {', '.join(names)}]\n")

    scraped_results = []
    if uncached_scripts:
        names = [s.get("competitor_name", "?") for s in uncached_scripts]
        if on_token:
            on_token(f"\n[Scraping {len(uncached_scripts)} competitors in parallel: {', '.join(names)}...]\n")

        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL, len(uncached_scripts))) as pool:
            futures = {
                pool.submit(_scrape_one, comp, on_token=on_token, on_usage=on_usage, use_model=model): comp
                for comp in uncached_scripts
            }
            for future in as_completed(futures):
                try:
                    scraped_results.append(future.result())
                except Exception as e:
                    comp = futures[future]
                    print(f"[Agent2] Thread error for {comp.get('competitor_name')}: {e}")
                    scraped_results.append({
                        "competitor_name": comp.get("competitor_name", "Unknown"),
                        "website": comp.get("website", ""),
                        "scrape_status": "failed", "errors": [str(e)],
                        "pricing": {}, "services": [], "reviews_summary": {},
                        "homepage_headline": "", "usps": [], "seo_keywords": []
                    })

        _store_cache(uncached_scripts, scraped_results)

    all_results = cached_results + scraped_results
    print(f"[Agent2] Total: {len(all_results)} competitors ({len(cached_results)} cached, {len(scraped_results)} scraped)")
    return all_results
