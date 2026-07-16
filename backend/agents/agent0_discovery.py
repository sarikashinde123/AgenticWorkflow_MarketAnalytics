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

_JSON_SHAPE = """
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
"""

SYSTEM_STRICT = """
You are Agent 0 — the Business Discovery agent in a competitive intelligence pipeline.

Your job: given a business name, type, location, and search radius, use web_search to:
1. Build a profile of the target business (website, USP, services)
2. Discover up to {{max_competitors}} real local competitors within the search radius
3. Return a structured JSON object

STRICT MATCHING MODE — ZERO TOLERANCE:
- ONLY include competitors that EXPLICITLY offer the EXACT SAME CORE SERVICE as the
  business type. Not the same industry. Not a related service. The EXACT service.
- For each candidate, ask: "Does this business SPECIFICALLY advertise / operate this
  exact service?" If the answer is not a clear YES from their listing or website,
  EXCLUDE them.
- Example: if the business type is "automatic car wash", ONLY include businesses that
  explicitly advertise automatic/machine car wash equipment. EXCLUDE:
    × Hand car wash centres (different service method)
    × Car detailing / coating studios (different service)
    × Car accessories / spare parts shops (different business)
    × Doorstep / mobile car wash services (different delivery model)
    × General "car wash" listings that don't mention automatic/machine wash
- If you CANNOT find any competitors offering the exact service, return an EMPTY
  competitors list. Do NOT substitute with loosely related businesses. An empty list
  is the CORRECT answer when no exact match exists.
- It is ALWAYS better to return 0-2 truly matching competitors than 6 loosely related ones.

IMPORTANT — Search Strategy:
- Use EXACTLY 2 web_search calls — no more. Make them count:
  1. Find the target business
  2. Find competitors nearby (combine directory + general search in one query)
- Include businesses from directory listings (JustDial, IndiaMART, Google Maps, etc.)
  even if they have no official website — use their directory URL.
- For the "website" field: use the business's own website if it exists. If not, use
  their best directory listing URL so downstream agents can still scrape information.

BEFORE adding any competitor to the list, verify:
  1. Does this business EXPLICITLY mention "{{business_type}}" on their listing/site?
  2. Is this their CORE service, not a minor add-on?
  If BOTH answers are not YES → DO NOT include them.
""" + _JSON_SHAPE + """
Use web_search to find real competitors. Prioritise businesses closest to the location.
EXCLUDE any business that does not EXPLICITLY offer the specified business type.
If no exact matches exist, return an empty competitors list — do NOT pad with related businesses.
Return ONLY the JSON — no markdown fences, no explanation.
"""

SYSTEM_GENERAL = """
You are Agent 0 — the Business Discovery agent in a competitive intelligence pipeline.

Your job: given a business name, type, location, and search radius, use web_search to:
1. Build a profile of the target business (website, USP, services)
2. Discover exactly {{max_competitors}} real local competitors within the search radius
3. Return a structured JSON object

GENERAL MATCHING MODE — Broad Discovery:
- Include competitors from the same INDUSTRY or CATEGORY, even if they don't offer the
  exact same service. For example, if the business type is "automatic car wash", also
  include hand car wash, car detailing, car spa, and car care centres — any business
  that competes for the same customers.
- Cast a wide net — local businesses without fancy websites are often the strongest competitors.

IMPORTANT — Search Strategy:
- Use EXACTLY 2 web_search calls — no more. Make them count:
  1. Find the target business
  2. Find competitors nearby (combine directory + general search in one query)
- Include businesses from directory listings (JustDial, IndiaMART, Google Maps, etc.)
  even if they have no official website — use their directory URL.
- For the "website" field: use the business's own website if it exists. If not, use
  their best directory listing URL so downstream agents can still scrape information.
""" + _JSON_SHAPE + """
Use web_search to find real competitors. Prioritise businesses closest to the location.
Include local businesses without fancy websites — they are often strong competitors.
Return ONLY the JSON — no markdown fences, no explanation.
"""


def run(business_name: str, business_type: str, location: str,
        search_radius_km: int, max_competitors: int = 6,
        strict_match: bool = False,
        latitude: float | None = None,
        longitude: float | None = None, on_token=None, on_usage=None,
        model: str | None = None) -> dict:
    """
    Runs Agent 0 and returns the input_schema dict.
    strict_match=True finds only exact-service competitors.
    strict_match=False finds broadly related competitors.
    """
    coords_line = ""
    if latitude is not None and longitude is not None:
        coords_line = f"GPS coordinates: {latitude}, {longitude} (use these for precise nearby search)\n"

    match_instruction = (
        f"STRICT MODE — ZERO TOLERANCE: Only include competitors that EXPLICITLY advertise \"{business_type}\" "
        f"as their core service. If a business does not clearly mention \"{business_type}\" on their listing, "
        f"EXCLUDE them. If you find ZERO exact matches, return an empty competitors list. "
        f"Do NOT pad the list with related-but-different businesses."
        if strict_match else
        f"GENERAL MODE: Include competitors from the broader \"{business_type}\" industry/category, "
        f"even if they offer a slightly different variant of the service."
    )

    prompt = (
        f"Business name: {business_name}\n"
        f"Business type: {business_type}\n"
        f"Location: {location}\n"
        f"{coords_line}"
        f"Search radius: {search_radius_km} km\n\n"
        "Run EXACTLY 2 web_search calls:\n"
        f"1. \"{business_name} {business_type} {location}\" (find the target business)\n"
        f"2. \"best {business_type} near {location} reviews ratings\" (find competitors)\n\n"
        f"{match_instruction}\n\n"
        "After these 2 searches, compile the results into JSON and return immediately. "
        "Do NOT run additional searches."
    )

    use_model = model or MODEL
    tpl = SYSTEM_STRICT if strict_match else SYSTEM_GENERAL
    system = tpl.format(max_competitors=max_competitors, business_type=business_type)
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
