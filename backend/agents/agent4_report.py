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


def run(input_schema: dict, analysis: dict, on_chunk=None) -> str:
    """
    Runs Agent 4 with streaming.
    on_chunk(text) is called for each streamed token.
    Returns the complete HTML string.
    """
    business = input_schema.get("business", {})

    prompt = (
        f"Business: {business.get('name')} ({business.get('type')}) — {business.get('location')}\n\n"
        f"Full Analysis:\n{json.dumps(analysis, indent=2)}\n\n"
        "Generate the complete competitive intelligence HTML report now."
    )

    full_html = ""

    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            full_html += text
            if on_chunk:
                on_chunk(text)

    return full_html
