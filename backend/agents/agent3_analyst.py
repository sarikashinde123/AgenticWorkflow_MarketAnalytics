"""
Agent 3 — Deep Analyst
Model  : claude-sonnet-4-6
Tool   : Extended Thinking
Output : analysis.json — SWOT, pricing table, SEO scores, review sentiment
"""
from __future__ import annotations
import json
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-sonnet-4-6"

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
    {"competitor": "...", "website": "...(from input data)", "source": "...(where found: google, justdial, indiamart etc.)",
     "rating": 0.0, "sentiment": "positive|neutral|negative",
     "top_positives": [], "top_negatives": []}
  ],
  "seo_analysis": [
    {"competitor": "...", "top_keywords": [], "estimated_authority": "high|medium|low"}
  ],
  "competitor_scores": [
    {"competitor": "...", "website": "...(from input data)", "source": "...(where found: google, justdial, indiamart etc.)",
     "threat_score": 0-10, "threat_level": "high|medium|low",
     "reasoning": "..."}
  ],
  "top_3_recommendations": ["...", "...", "..."],
  "gaps_and_opportunities": ["...", "..."],
  "best_location": {
    "recommended_area": "specific locality/neighbourhood name within the search radius",
    "why": "2-3 sentence explanation of why this area is ideal",
    "competitor_density": "low|medium|high — how many competitors already operate here",
    "demand_signals": ["list of factors indicating strong customer demand in this area"],
    "avoid_areas": [
      {"area": "locality name", "reason": "why this area is a poor choice (e.g. oversaturated, low footfall)"}
    ]
  }
}

BEST LOCATION ANALYSIS: Based on where competitors are clustered (their addresses),
identify the area within the search radius that has the LEAST competitor saturation
but strong demand potential. Consider: residential density, commercial activity,
proximity to complementary businesses, footfall, and accessibility.
Flag areas to AVOID due to heavy competitor presence.

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
    {"competitor": "...", "website": "...(from input data)", "source": "...(where found: google, justdial, indiamart etc.)", "rating": 0.0, "sentiment": "positive|neutral|negative", "top_positives": [], "top_negatives": []}
  ],
  "seo_analysis": [
    {"competitor": "...", "top_keywords": [], "estimated_authority": "high|medium|low"}
  ],
  "competitor_scores": [
    {"competitor": "...", "website": "...(from input data)", "source": "...(where found: google, justdial, indiamart etc.)", "threat_score": 0-10, "threat_level": "high|medium|low", "reasoning": "..."}
  ],
  "gap_analysis": {
    "missing_services": [ {"service": "...", "offered_by": ["..."], "impact": "..."} ],
    "pricing_gaps":     [ {"area": "...", "your_price": "...", "market_price": "...", "assessment": "..."} ],
    "feature_gaps":     [ {"feature": "...", "competitors_with_it": ["..."], "recommendation": "..."} ],
    "trust_gaps":       [ {"issue": "...", "detail": "..."} ],
    "your_advantages":  [ "things WE already do better than the market" ]
  },
  "quick_wins": [ "low-effort, high-impact fixes to close gaps fast" ],
  "top_3_recommendations": [ "prioritised actions to close the biggest gaps", "...", "..." ],
  "best_location": {
    "recommended_area": "specific locality/neighbourhood name within the search radius",
    "why": "2-3 sentence explanation of why this area is ideal",
    "competitor_density": "low|medium|high — how many competitors already operate here",
    "demand_signals": ["list of factors indicating strong customer demand in this area"],
    "avoid_areas": [
      {"area": "locality name", "reason": "why this area is a poor choice (e.g. oversaturated, low footfall)"}
    ]
  }
}

BEST LOCATION ANALYSIS: Based on where competitors are clustered (their addresses),
identify the area within the search radius that has the LEAST competitor saturation
but strong demand potential. Consider: residential density, commercial activity,
proximity to complementary businesses, footfall, and accessibility.
Flag areas to AVOID due to heavy competitor presence.

IMPORTANT: The feature_matrix MUST include a "You" column built from OUR offerings, alongside each
competitor. The pricing_comparison MUST include a row for OUR business using OUR actual prices.
Ground every gap in real competitor data and our real offerings. Return ONLY the JSON.
"""


def _extract_json(text: str) -> dict | None:
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
            if p.startswith("{"):
                try:
                    return json.loads(p)
                except json.JSONDecodeError:
                    pass
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


def run(input_schema: dict, raw_data: list[dict], mode: str = "market_overview",
        own_offerings: str | None = None, on_token=None, on_usage=None,
        model: str | None = None) -> dict:
    """
    Runs Agent 3 with adaptive thinking and returns the analysis dict.
    In gap_analysis mode it also folds in the user's own offerings.
    """
    business = input_schema.get("business", {})

    location = input_schema.get("location", business.get("location", ""))
    radius = input_schema.get("search_radius_km", 5)

    location_context = (
        f"\nSearch Area: {location} within {radius} km radius.\n"
        f"Competitor Addresses (use these to identify clusters and gaps):\n"
    )
    for c in input_schema.get("competitors", []):
        addr = c.get("address", "unknown")
        location_context += f"  - {c.get('name', '?')}: {addr}\n"

    if mode == "gap_analysis":
        system = GAP_SYSTEM
        prompt = (
            f"Our Business:\n{json.dumps(business, indent=2)}\n\n"
            f"{location_context}\n"
            f"OUR OWN OFFERINGS (from the owner's document):\n{(own_offerings or 'Not provided').strip()[:16000]}\n\n"
            f"Raw Competitor Data:\n{json.dumps(raw_data, indent=2)}\n\n"
            "Compare our offerings against the market and return the structured gap-analysis JSON."
        )
    else:
        system = SYSTEM
        prompt = (
            f"Our Business:\n{json.dumps(business, indent=2)}\n\n"
            f"{location_context}\n"
            f"Raw Competitor Data:\n{json.dumps(raw_data, indent=2)}\n\n"
            "Perform a deep competitive analysis. Return the structured JSON."
        )

    use_model = model or MODEL
    thinking_cfg = (
        {"type": "adaptive"}
        if use_model.startswith("claude-opus")
        else {"type": "enabled", "budget_tokens": 8000}
    )
    response = client.messages.create(
        model=use_model,
        max_tokens=16000,
        thinking=thinking_cfg,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if on_usage:
        on_usage(response.usage)

    full_text = ""
    for block in response.content:
        if block.type == "thinking" and on_token:
            on_token(f"[thinking...]\n")
        if hasattr(block, "text"):
            full_text += block.text
            if on_token:
                on_token(block.text)

    parsed = _extract_json(full_text)
    if parsed:
        print(f"[Agent3] Analysis parsed: {list(parsed.keys())}")
        print(f"[Agent3] competitor_scores={len(parsed.get('competitor_scores', []))}, "
              f"pricing={len(parsed.get('pricing_comparison', []))}, "
              f"features={len(parsed.get('feature_matrix', {}).get('features', []))}")
        return parsed

    print(f"[Agent3] JSON parse FAILED, raw length={len(full_text)}")
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
