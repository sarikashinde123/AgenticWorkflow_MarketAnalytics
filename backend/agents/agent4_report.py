"""
Agent 4 — Report Writer
Model  : claude-opus-4-8
Tool   : Streaming API
Output : report.html (streamed token by token to SSE)
"""
from __future__ import annotations
import json
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-opus-4-8"

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
7. SEO Analysis — keyword clouds per competitor
8. SWOT Analysis — 2x2 grid
9. Gaps & Opportunities — highlighted cards
10. Top 3 Recommendations — numbered, bold, actionable
11. Footer — generated timestamp, confidential label

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
10. Quick Wins — low-effort, high-impact fixes (highlighted)
11. Action Plan to Close the Gaps — the top 3 recommendations, numbered and specific
12. Footer — generated timestamp, confidential label

OUTPUT: Complete valid HTML document starting with <!DOCTYPE html>
Real data only — zero placeholders.
"""


def run(input_schema: dict, analysis: dict, mode: str = "market_overview", on_chunk=None, on_usage=None) -> str:
    """
    Runs Agent 4 with streaming.
    on_chunk(text) is called for each streamed token.
    Returns the complete HTML string.
    """
    business = input_schema.get("business", {})
    system = GAP_SYSTEM if mode == "gap_analysis" else SYSTEM
    kind = "gap-analysis" if mode == "gap_analysis" else "competitive intelligence"

    prompt = (
        f"Business: {business.get('name')} ({business.get('type')}) — {business.get('location')}\n\n"
        f"Full Analysis:\n{json.dumps(analysis, indent=2)}\n\n"
        f"Generate the complete {kind} HTML report now."
    )

    full_html = ""

    with client.messages.stream(
        model=MODEL,
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

    return full_html
