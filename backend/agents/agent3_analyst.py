"""
Agent 3 — Deep Analyst
Model  : claude-opus-4-8
Tool   : Extended Thinking
Output : analysis.json — SWOT, pricing table, SEO scores, review sentiment
"""
from __future__ import annotations
import json
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-opus-4-8"

SYSTEM = """
You are Agent 3 — the Deep Analyst in a competitive intelligence pipeline.

You receive raw competitor data and our business profile. Using extended thinking,
produce a deep competitive analysis JSON with these keys:

{
  "executive_summary": "3-4 sentence strategic insight",
  "swot": {
    "strengths": [], "weaknesses": [], "opportunities": [], "threats": []
  },
  "pricing_comparison": [
    {"competitor": "...", "price_range": "...", "value_score": 0-10, "notes": "..."}
  ],
  "feature_matrix": {
    "features": [],
    "competitors": {
      "CompetitorName": {"FeatureName": true|false}
    }
  },
  "review_sentiment": [
    {"competitor": "...", "rating": 0.0, "sentiment": "positive|neutral|negative",
     "top_positives": [], "top_negatives": []}
  ],
  "seo_analysis": [
    {"competitor": "...", "top_keywords": [], "estimated_authority": "high|medium|low"}
  ],
  "competitor_scores": [
    {"competitor": "...", "threat_score": 0-10, "threat_level": "high|medium|low",
     "reasoning": "..."}
  ],
  "top_3_recommendations": ["...", "...", "..."],
  "gaps_and_opportunities": ["...", "..."]
}

Think deeply. Be specific. Use only real data from the raw input.
Return ONLY the JSON.
"""


# Gap Analysis mode — the user runs an existing business and has provided their
# OWN offerings. Compare them against the market and pinpoint concrete gaps.
GAP_SYSTEM = """
You are Agent 3 — the Deep Analyst in a competitive intelligence pipeline, running in GAP ANALYSIS mode.

You receive: (1) our business profile, (2) OUR OWN OFFERINGS (services, pricing, features — parsed
from a document the owner provided), and (3) raw competitor data. Using extended thinking, compare
OUR offerings against the market and produce a JSON that makes the gaps explicit and actionable:

{
  "executive_summary": "3-4 sentences: where we stand vs the market and our biggest gaps",
  "your_offerings_summary": "concise summary of OUR services, pricing and features from the provided document",
  "swot": { "strengths": [], "weaknesses": [], "opportunities": [], "threats": [] },
  "pricing_comparison": [
    {"competitor": "...", "price_range": "...", "value_score": 0-10, "notes": "..."}
  ],
  "feature_matrix": {
    "features": [],
    "competitors": { "You": {"FeatureName": true|false}, "CompetitorName": {"FeatureName": true|false} }
  },
  "review_sentiment": [
    {"competitor": "...", "rating": 0.0, "sentiment": "positive|neutral|negative", "top_positives": [], "top_negatives": []}
  ],
  "seo_analysis": [
    {"competitor": "...", "top_keywords": [], "estimated_authority": "high|medium|low"}
  ],
  "competitor_scores": [
    {"competitor": "...", "threat_score": 0-10, "threat_level": "high|medium|low", "reasoning": "..."}
  ],
  "gap_analysis": {
    "missing_services": [ {"service": "...", "offered_by": ["..."], "impact": "..."} ],
    "pricing_gaps":     [ {"area": "...", "your_price": "...", "market_price": "...", "assessment": "..."} ],
    "feature_gaps":     [ {"feature": "...", "competitors_with_it": ["..."], "recommendation": "..."} ],
    "trust_gaps":       [ {"issue": "...", "detail": "..."} ],
    "your_advantages":  [ "things WE already do better than the market" ]
  },
  "quick_wins": [ "low-effort, high-impact fixes to close gaps fast" ],
  "top_3_recommendations": [ "prioritised actions to close the biggest gaps", "...", "..." ]
}

IMPORTANT: The feature_matrix MUST include a "You" column built from OUR offerings, alongside each
competitor. The pricing_comparison MUST include a row for OUR business using OUR actual prices.
Ground every gap in real competitor data and our real offerings. Return ONLY the JSON.
"""


def run(input_schema: dict, raw_data: list[dict], mode: str = "market_overview",
        own_offerings: str | None = None, on_token=None) -> dict:
    """
    Runs Agent 3 with adaptive thinking and returns the analysis dict.
    In gap_analysis mode it also folds in the user's own offerings.
    """
    business = input_schema.get("business", {})

    if mode == "gap_analysis":
        system = GAP_SYSTEM
        prompt = (
            f"Our Business:\n{json.dumps(business, indent=2)}\n\n"
            f"OUR OWN OFFERINGS (from the owner's document):\n{(own_offerings or 'Not provided').strip()[:16000]}\n\n"
            f"Raw Competitor Data:\n{json.dumps(raw_data, indent=2)}\n\n"
            "Compare our offerings against the market and return the structured gap-analysis JSON."
        )
    else:
        system = SYSTEM
        prompt = (
            f"Our Business:\n{json.dumps(business, indent=2)}\n\n"
            f"Raw Competitor Data:\n{json.dumps(raw_data, indent=2)}\n\n"
            "Perform a deep competitive analysis. Return the structured JSON."
        )

    # Adaptive thinking — claude-opus-4-8 controls thinking depth itself;
    # effort tunes how deeply it reasons (budget_tokens is rejected on this model)
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    full_text = ""
    for block in response.content:
        if block.type == "thinking" and on_token:
            on_token(f"[thinking...]\n")
        if hasattr(block, "text"):
            full_text += block.text
            if on_token:
                on_token(block.text)

    try:
        clean = full_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except json.JSONDecodeError:
        return {
            "executive_summary": "Analysis could not be parsed.",
            "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
            "pricing_comparison": [],
            "feature_matrix": {"features": [], "competitors": {}},
            "review_sentiment": [],
            "seo_analysis": [],
            "competitor_scores": [],
            "top_3_recommendations": [],
            "gaps_and_opportunities": []
        }
