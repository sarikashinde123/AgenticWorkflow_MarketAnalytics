"""
Agent 4 — Report Writer
Model  : claude-sonnet-4-6
Tool   : Streaming API
Output : report.html (streamed token by token to SSE)
"""
from __future__ import annotations
import json
import re
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-sonnet-4-6"

SYSTEM = """
You are Agent 4 — the Report Writer in a competitive intelligence pipeline.

Generate a complete, self-contained HTML competitive intelligence report.

DESIGN:
- Dark theme: bg #060d1f, cards #0f172a, accent #818cf8, text #e2e8f0
- Inline CSS only — no external files or CDN links
- Responsive layout
- Professional typography

REQUIRED SECTIONS:
1. Header — business name, report date, tagline
2. Executive Summary — insight-rich, 3-4 sentences
3. Competitor Threat Scores — CSS progress bars, color-coded
4. Pricing Comparison — table with our advantage highlighted in green
5. Feature Matrix — ✓ / ✗ grid
6. Review Sentiment — star ratings + sentiment badges
7. Best Location to Start — a highlighted card showing the recommended area,
   why it's ideal, demand signals as bullet points, and a list of areas to avoid
   (with reasons). Use a map-pin icon or location emoji. Data is in best_location{}.
8. Gaps & Opportunities — highlighted cards
9. Top 3 Recommendations — numbered, bold, actionable
10. Footer — generated timestamp, confidential label

Do NOT include SEO Analysis or SWOT Analysis sections.

COMPETITOR WEBSITE LINKS (MANDATORY):
- In the Review Sentiment section and Competitor Threat Scores section, EVERY competitor
  card/row MUST have a "Visit Website ↗" link next to the competitor name IF the "website"
  field is present and non-empty in the analysis data.
- HTML pattern to use:
  <a href="THE_URL" target="_blank" rel="noopener"
     style="display:inline-block;margin-left:10px;background:rgba(129,140,248,0.18);
     color:#818cf8;font-size:0.75rem;padding:3px 12px;border-radius:12px;
     text-decoration:none;vertical-align:middle;">Visit Website ↗</a>
- Place it right after the <h3> or <strong> competitor name, on the same line.
- The "website" field is in review_sentiment[].website and competitor_scores[].website.

SOURCE BADGES (MANDATORY):
- Right after the "Visit Website ↗" pill, add a source badge showing where the competitor
  was found (e.g. JustDial, Google, IndiaMart, Sulekha, etc.) IF the "source" field exists.
- HTML pattern to use:
  <span style="display:inline-block;margin-left:6px;background:rgba(245,165,36,0.15);
  color:#f5a524;font-size:0.65rem;padding:2px 8px;border-radius:10px;
  font-weight:600;letter-spacing:0.03em;">SOURCE_NAME</span>
- The "source" field is in competitor_scores[].source and review_sentiment[].source.

OUTPUT: Complete valid HTML document starting with <!DOCTYPE html>
Real data only — zero placeholders.
"""


# Gap Analysis report — leads with where the business stands vs the market and
# what to fix. Uses the SAME visual design as the overview report.
GAP_SYSTEM = """
You are Agent 4 — the Report Writer in a competitive intelligence pipeline, running in GAP ANALYSIS mode.

Generate a complete, self-contained HTML report that benchmarks OUR business against the market
and makes the gaps unmissable and actionable.

DESIGN:
- Dark theme: bg #060d1f, cards #0f172a, accent #818cf8, text #e2e8f0
- Inline CSS only — no external files or CDN links
- Responsive layout, professional typography

REQUIRED SECTIONS (in this order):
1. Header — business name, "Gap Analysis" label, report date
2. Executive Summary — where we stand vs the market and our biggest gaps
3. Your Offerings at a Glance — summary of OUR current services/pricing/features
4. Identified Gaps — the centrepiece. Group into: Missing Services, Pricing Gaps, Feature Gaps,
   Trust Gaps. Use colour-coded cards; make each gap concrete (what's missing, who has it, why it matters)
5. Where You Win — our advantages over the market (green cards)
6. Pricing Comparison — table INCLUDING our own row, highlighting where we're over/under-priced
7. Feature Matrix — grid with a "You" column beside each competitor; mark our ✗ gaps clearly
8. Competitor Threat Scores — CSS bars, colour-coded
9. Review Sentiment — star ratings + sentiment badges
10. Best Location to Start / Expand — a highlighted card showing the recommended area,
    why it's ideal, demand signals as bullet points, and areas to avoid (with reasons).
    Use a map-pin icon or location emoji. Data is in best_location{}.
11. Quick Wins — low-effort, high-impact fixes (highlighted)
12. Action Plan to Close the Gaps — the top 3 recommendations, numbered and specific
13. Footer — generated timestamp, confidential label

COMPETITOR WEBSITE LINKS (MANDATORY):
- In the Review Sentiment section and Competitor Threat Scores section, EVERY competitor
  card/row MUST have a "Visit Website ↗" link next to the competitor name IF the "website"
  field is present and non-empty in the analysis data.
- HTML pattern to use:
  <a href="THE_URL" target="_blank" rel="noopener"
     style="display:inline-block;margin-left:10px;background:rgba(129,140,248,0.18);
     color:#818cf8;font-size:0.75rem;padding:3px 12px;border-radius:12px;
     text-decoration:none;vertical-align:middle;">Visit Website ↗</a>
- Place it right after the <h3> or <strong> competitor name, on the same line.
- The "website" field is in review_sentiment[].website and competitor_scores[].website.

SOURCE BADGES (MANDATORY):
- Right after the "Visit Website ↗" pill, add a source badge showing where the competitor
  was found (e.g. JustDial, Google, IndiaMart, Sulekha, etc.) IF the "source" field exists.
- HTML pattern to use:
  <span style="display:inline-block;margin-left:6px;background:rgba(245,165,36,0.15);
  color:#f5a524;font-size:0.65rem;padding:2px 8px;border-radius:10px;
  font-weight:600;letter-spacing:0.03em;">SOURCE_NAME</span>
- The "source" field is in competitor_scores[].source and review_sentiment[].source.

OUTPUT: Complete valid HTML document starting with <!DOCTYPE html>
Real data only — zero placeholders.
"""


VISIT_PILL = (
    '<a href="{url}" target="_blank" rel="noopener" style="display:inline-block;'
    'margin-left:10px;background:rgba(129,140,248,0.18);color:#818cf8;'
    'font-size:0.75rem;padding:3px 12px;border-radius:12px;text-decoration:none;'
    'vertical-align:middle;">Visit Website ↗</a>'
)

SOURCE_BADGE = (
    '<span style="display:inline-block;margin-left:6px;background:rgba(245,165,36,0.15);'
    'color:#f5a524;font-size:0.65rem;padding:2px 8px;border-radius:10px;'
    'vertical-align:middle;font-weight:600;letter-spacing:0.03em;">{source}</span>'
)


def _inject_website_buttons(html: str, website_map: dict[str, str], source_map: dict[str, str]) -> str:
    """Post-process HTML to inject 'Visit Website' pill buttons and source badges next to competitor names."""
    for name, url in website_map.items():
        if not url:
            continue
        pill = VISIT_PILL.format(url=url)
        source = source_map.get(name, "")
        badge = SOURCE_BADGE.format(source=source) if source else ""
        combined = f" {pill}{badge}"
        for tag in ["h2", "h3", "h4"]:
            pattern = re.compile(
                rf"(<{tag}[^>]*>)(.*?)({re.escape(name)})(.*?)(</{tag}>)",
                re.IGNORECASE,
            )
            html = pattern.sub(rf"\1\2\3{combined}\4\5", html, count=0)
        for tag in ["strong", "b"]:
            pattern = re.compile(
                rf"(<{tag}[^>]*>)(.*?)({re.escape(name)})(.*?)(</{tag}>)",
                re.IGNORECASE,
            )
            html = pattern.sub(rf"\1\2\3{combined}\4\5", html, count=0)
    return html


def run(input_schema: dict, analysis: dict, mode: str = "market_overview", on_chunk=None, on_usage=None, model: str | None = None) -> str:
    """
    Runs Agent 4 with streaming.
    on_chunk(text) is called for each streamed token.
    Returns the complete HTML string with website buttons injected.
    """
    business = input_schema.get("business", {})
    system = GAP_SYSTEM if mode == "gap_analysis" else SYSTEM
    kind = "gap-analysis" if mode == "gap_analysis" else "competitive intelligence"

    # Remove SEO and SWOT data so the LLM doesn't generate those sections
    filtered_analysis = {k: v for k, v in analysis.items() if k not in ("seo_analysis", "swot")}

    prompt = (
        f"Business: {business.get('name')} ({business.get('type')}) — {business.get('location')}\n\n"
        f"Full Analysis:\n{json.dumps(filtered_analysis, indent=2)}\n\n"
        f"Generate the complete {kind} HTML report now."
    )

    full_html = ""

    with client.messages.stream(
        model=model or MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            full_html += text
            if on_chunk:
                on_chunk(text)
        if on_usage:
            on_usage(stream.get_final_message().usage)

    # Build name → URL and name → source maps from input_schema competitors
    website_map: dict[str, str] = {}
    source_map: dict[str, str] = {}
    for c in input_schema.get("competitors", []):
        name = c.get("name", "").strip()
        url = c.get("website", "").strip()
        source = c.get("source", "").strip()
        if name and url:
            website_map[name] = url
        if name and source:
            source_map[name] = source

    # Inject "Visit Website ↗" buttons and source badges next to competitor names
    if website_map:
        full_html = _inject_website_buttons(full_html, website_map, source_map)

    return full_html
