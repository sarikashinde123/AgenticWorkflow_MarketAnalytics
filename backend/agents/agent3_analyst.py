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


def run(input_schema: dict, raw_data: list[dict], on_token=None) -> dict:
    """
    Runs Agent 3 with Extended Thinking and returns the analysis dict.
    """
    business = input_schema.get("business", {})

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
        system=SYSTEM,
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
