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

SYSTEM_TEMPLATE = """
You are Agent 0 — the Business Discovery agent in a competitive intelligence pipeline.

Your job: given a business name, type, location, and search radius, use web_search to:
1. Build a profile of the target business (website, USP, services)
2. Discover exactly {max_competitors} real local competitors within the search radius
3. Return a structured JSON object

IMPORTANT — Search Strategy:
- Use EXACTLY 2 web_search calls — no more. Make them count:
  1. Find the target business
  2. Find competitors nearby (combine directory + general search in one query)
- Include businesses from directory listings (JustDial, IndiaMART, Google Maps, etc.)
  even if they have no official website — use their directory URL.
- For the "website" field: use the business's own website if it exists. If not, use
  their best directory listing URL so downstream agents can still scrape information.

Output ONLY a valid JSON object with this exact shape:
{{
  "business": {{
    "name": "...",
    "type": "...",
    "location": "...",
    "website": "...",
    "description": "...",
    "usp": "..."
  }},
  "competitors": [
    {{
      "name": "...",
      "website": "... (official site OR best directory listing URL)",
      "address": "...",
      "phone": "...",
      "source": "... (where you found them: google, justdial, indiamart, etc.)",
      "priority": "high|medium|low",
      "notes": "..."
    }}
  ],
  "search_radius_km": 5,
  "location": "..."
}}

Use web_search to find real competitors. Prioritise businesses closest to the location.
Cast a wide net — local businesses without fancy websites are often the strongest competitors.
Return ONLY the JSON — no markdown fences, no explanation.
"""


def run(business_name: str, business_type: str, location: str,
        search_radius_km: int, max_competitors: int = 6,
        latitude: float | None = None,
        longitude: float | None = None, on_token=None, on_usage=None,
        model: str | None = None) -> dict:
    """
    Runs Agent 0 and returns the input_schema dict.
    on_token(text) is called for each streamed token if provided.
    on_usage(response.usage) is called after each API call for token accounting.
    """
    coords_line = ""
    if latitude is not None and longitude is not None:
        coords_line = f"GPS coordinates: {latitude}, {longitude} (use these for precise nearby search)\n"

    prompt = (
        f"Business name: {business_name}\n"
        f"Business type: {business_type}\n"
        f"Location: {location}\n"
        f"{coords_line}"
        f"Search radius: {search_radius_km} km\n\n"
        "Run EXACTLY 2 web_search calls:\n"
        f"1. \"{business_name} {business_type} {location}\" (find the target business)\n"
        f"2. \"best {business_type} near {location} reviews ratings\" (find competitors)\n\n"
        "After these 2 searches, compile the results into JSON and return immediately. "
        "Do NOT run additional searches."
    )

    use_model = model or MODEL
    system = SYSTEM_TEMPLATE.format(max_competitors=max_competitors)
    messages = [{"role": "user", "content": prompt}]
    full_text = ""

    MAX_LOOPS = 3
    loop_count = 0
    while loop_count < MAX_LOOPS:
        loop_count += 1
        print(f"[Agent0] API call #{loop_count}/{MAX_LOOPS}, model={use_model}, messages count: {len(messages)}")
        response = client.messages.create(
            model=use_model,
            max_tokens=4096,
            system=system,
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        )
        if on_usage:
            on_usage(response.usage)

        print(f"[Agent0] stop_reason={response.stop_reason}, content blocks: {len(response.content)}")
        for i, block in enumerate(response.content):
            btype = getattr(block, "type", "unknown")
            print(f"[Agent0]   block[{i}] type={btype}")

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
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Search executed.",
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            print(f"[Agent0] Unexpected stop_reason: {response.stop_reason}")
            break

    # Parse the JSON from the final text
    import re
    print(f"[Agent0] Raw output length: {len(full_text)} chars")
    print(f"[Agent0] Raw output (first 500): {full_text[:500]}")

    def _extract_json(text: str) -> dict | None:
        """Try multiple strategies to extract JSON from the model output."""
        clean = text.strip()

        # Strategy 1: direct parse
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        # Strategy 2: strip markdown fences
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

        # Strategy 3: find the outermost { ... } in the text
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

    parsed = _extract_json(full_text)
    if parsed and isinstance(parsed.get("competitors"), list):
        print(f"[Agent0] Parsed {len(parsed['competitors'])} competitors")
        return parsed

    print(f"[Agent0] JSON parsing FAILED — returning fallback with 0 competitors")
    return {
        "business": {
            "name": business_name, "type": business_type,
            "location": location, "website": "", "description": "", "usp": ""
        },
        "competitors": [],
        "search_radius_km": search_radius_km,
        "location": location,
    }
