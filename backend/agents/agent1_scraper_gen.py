"""
Agent 1 — Scraper Generator
Model  : claude-opus-4-8
Tool   : Tool Use API (structured output)
Output : scraper_scripts[] — per-competitor scrape instruction JSON
"""
from __future__ import annotations
import json
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-opus-4-8"

SYSTEM = """
You are Agent 1 — the Scraper Generator in a competitive intelligence pipeline.

Given a list of competitors from input_schema.json, use the save_scraper_instructions tool
to produce a structured scrape instruction set for each competitor.

For each competitor call save_scraper_instructions with:
- competitor_name
- website
- search_queries: 3-5 targeted web_search queries to gather intel
- target_data: list of data points to extract (pricing, services, reviews, etc.)
- priority
"""

TOOLS = [
    {
        "name": "save_scraper_instructions",
        "description": "Saves structured scrape instructions for one competitor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "competitor_name": {"type": "string"},
                "website": {"type": "string"},
                "search_queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-5 web_search queries to run for this competitor"
                },
                "target_data": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Data points to extract: pricing, services, reviews, hours, contact"
                },
                "priority": {"type": "string", "enum": ["high", "medium", "low"]}
            },
            "required": ["competitor_name", "website", "search_queries", "target_data", "priority"]
        }
    }
]


def run(input_schema: dict, on_token=None, on_usage=None) -> list[dict]:
    """
    Runs Agent 1 and returns a list of scraper instruction dicts.
    """
    scripts: list[dict] = []

    def handle_tool(inputs: dict) -> str:
        scripts.append(inputs)
        return f"Saved instructions for {inputs['competitor_name']}"

    tool_fns = {"save_scraper_instructions": lambda **k: handle_tool(k)}

    competitors = input_schema.get("competitors", [])
    business = input_schema.get("business", {})

    prompt = (
        f"Business: {business.get('name')} ({business.get('type')}) in {business.get('location')}\n\n"
        f"Competitors to generate scrape instructions for:\n"
        + "\n".join(
            f"- {c['name']} | {c.get('website','unknown')} | priority: {c.get('priority','medium')}"
            for c in competitors
        )
        + "\n\nCall save_scraper_instructions for EACH competitor."
    )

    messages = [{"role": "user", "content": prompt}]

    # Agentic loop
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        if on_usage:
            on_usage(response.usage)

        for block in response.content:
            if hasattr(block, "text") and on_token:
                on_token(block.text)

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    fn = tool_fns.get(block.name)
                    result = fn(**(block.input or {})) if fn else f"Unknown tool: {block.name}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return scripts
