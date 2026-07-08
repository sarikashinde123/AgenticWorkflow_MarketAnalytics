"""
Agent 0 — Business Discovery
Model  : claude-sonnet-4-6
Tool   : web_search (Claude native)
Output : input_schema.json — business profile + competitors list
"""
from __future__ import annotations
import json
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-sonnet-4-6"

# Claude's built-in web_search tool
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}

SYSTEM = """
You are Agent 0 — the Business Discovery agent in a competitive intelligence pipeline.

Your job: given a business name, type, location, and search radius, use web_search to:
1. Build a profile of the target business (website, USP, services)
2. Discover 4-6 real local competitors within the search radius
3. Return a structured JSON object

Output ONLY a valid JSON object with this exact shape:
{
  "business": {
    "name": "...",
    "type": "...",
    "location": "...",
    "website": "...",
    "description": "...",
    "usp": "..."
  },
  "competitors": [
    {
      "name": "...",
      "website": "...",
      "address": "...",
      "priority": "high|medium|low",
      "notes": "..."
    }
  ],
  "search_radius_km": 5,
  "location": "..."
}

Use web_search to find real competitors. Prioritise businesses closest to the location.
Return ONLY the JSON — no markdown fences, no explanation.
"""


def run(business_name: str, business_type: str, location: str,
        search_radius_km: int, on_token=None, on_usage=None) -> dict:
    """
    Runs Agent 0 and returns the input_schema dict.
    on_token(text) is called for each streamed token if provided.
    on_usage(response.usage) is called after each API call for token accounting.
    """
    prompt = (
        f"Business name: {business_name}\n"
        f"Business type: {business_type}\n"
        f"Location: {location}\n"
        f"Search radius: {search_radius_km} km\n\n"
        "Discover this business and find its top 4-6 local competitors. "
        "Return the structured JSON."
    )

    messages = [{"role": "user", "content": prompt}]
    full_text = ""

    # Agentic loop with web_search
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

        # Collect text from this response turn
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
                    # web_search results are returned by Claude automatically
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Search executed.",
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    # Parse the JSON from the final text
    try:
        # Strip markdown fences if present
        clean = full_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except json.JSONDecodeError:
        # Fallback: build minimal schema from input
        return {
            "business": {
                "name": business_name, "type": business_type,
                "location": location, "website": "", "description": "", "usp": ""
            },
            "competitors": [],
            "search_radius_km": search_radius_km,
            "location": location,
        }
