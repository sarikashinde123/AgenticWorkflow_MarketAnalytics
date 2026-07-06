# 🤖 Agentic Competitive Intelligence System
### Multi-Agent | Anthropic Claude SDK | Playwright | Python + Jupyter

---

## 📁 Project Structure

```
files/
├── input_schema.json                ← ✏️  EDIT THIS — your business + competitors
├── .env                             ← ✏️  Add your ANTHROPIC_API_KEY here
│
├── 01_agent1_prompt_engineer.ipynb  ← Generates Playwright scraper scripts
├── 02_agent2_scraper_runner.ipynb   ← Executes scrapers + HTTP fallback
├── 03_agent3_analyst.ipynb          ← Analyses raw data into intelligence
├── 04_agent4_report_writer.ipynb    ← Generates HTML/PDF report
├── 05_orchestrator.ipynb            ← 🔥 Runs ALL 4 agents in one shot
│
├── scripts/                         ← Auto-generated Playwright .py files
├── data/
│   ├── raw/                         ← Scraped JSON per competitor
│   ├── analysed/                    ← Structured analysis JSON
│   └── logs/                        ← Scrape run logs
└── reports/
    ├── competitive_report_latest.html
    ├── competitive_report_latest.pdf
    └── executive_summary.md
```

---

## ⚡ Quick Start (5 steps)

### 1. Install dependencies
```bash
# Activate your venv first
.venv\Scripts\activate

pip install anthropic python-dotenv playwright weasyprint jinja2
playwright install chromium
```

### 2. Set API key in `.env`
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```
Get your key at: https://console.anthropic.com/

### 3. Edit `input_schema.json`
Change the business name, description, and competitor URLs to match your use case.

### 4. Run the orchestrator
Open `05_orchestrator.ipynb` → Select venv kernel → **Run All Cells**

### 5. View report
The report opens automatically in your browser from `reports/competitive_report_latest.html`

---

## 🤖 Claude Models Used

| Agent | Model | Why |
|---|---|---|
| Agent 1 — Prompt Engineer | `claude-opus-4-8` | Complex code generation |
| Agent 2 — Scraper Runner | `claude-haiku-4-5-20251001` | Fast, cheap execution logic |
| Agent 3 — Analyst | `claude-opus-4-8` | Deep reasoning for analysis |
| Agent 4 — Report Writer | `claude-opus-4-8` | Large HTML document generation |

---

## 🔄 Run Individual Agents

Use individual notebooks to debug or re-run a single stage:

| Notebook | Runs | When to use |
|---|---|---|
| `01_agent1...` | Script generator | Change what to scrape |
| `02_agent2...` | Scraper executor | Re-scrape after script changes |
| `03_agent3...` | Data analyser | Re-analyse without re-scraping |
| `04_agent4...` | Report writer | Regenerate report only |
| `05_orchestrator` | Everything | Full fresh run |

---

## 🔁 How the Agentic Loop Works (Anthropic SDK)

Each notebook uses the same `run_claude_agent()` pattern:

```python
import anthropic
client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from .env

def run_claude_agent(system, tools, tool_fns, prompt, model, max_tokens):
    messages = [{"role": "user", "content": prompt}]
    while True:
        response = client.messages.create(
            model=model, max_tokens=max_tokens,
            system=system, tools=tools, messages=messages
        )
        if response.stop_reason == "end_turn":
            return final_text          # ← done

        if response.stop_reason == "tool_use":
            # Execute each tool Claude called
            for block in response.content:
                if block.type == "tool_use":
                    result = tool_fns[block.name](**block.input)
            # Feed results back — Claude decides what to do next
            messages.append(tool_results)
```

Tools are plain Python dicts (no decorators needed):
```python
TOOLS = [
    {
        "name": "my_tool",
        "description": "What it does",
        "input_schema": {
            "type": "object",
            "properties": {"arg1": {"type": "string"}},
            "required": ["arg1"]
        }
    }
]
```

---

## ✏️ Customising `input_schema.json`

```json
{
  "business": {
    "name": "YOUR COMPANY",
    "type": "YOUR INDUSTRY",
    "description": "What you do",
    "usp": "Your unique value"
  },
  "competitors": [
    { "name": "Competitor A", "website": "https://...", "priority": "high" },
    { "name": "Competitor B", "website": "https://...", "priority": "medium" }
  ],
  "scrape_targets": {
    "pricing": true,
    "features": true,
    "reviews": true,
    "homepage_messaging": true,
    "service_areas": true
  }
}
```

---

## 🛡️ Anti-Bot Tips

If competitors block scraping:
- Agent 2 automatically falls back to basic HTTP scraper
- Add delays in generated scripts (already built in by Agent 1)
- For heavily protected sites (Cloudflare): use ScraperAPI or Zyte as proxy

---

## ⚠️ Troubleshooting

| Issue | Fix |
|---|---|
| `ANTHROPIC_API_KEY not found` | Check `.env` file has the correct key |
| `playwright install` not found | Run `python -m playwright install chromium` |
| Scripts not generated | Check Agent 1 output — look for tool call errors |
| All scrapers failing | Run `02_agent2` individually to see error detail |
| WeasyPrint PDF error | Open HTML in Chrome → Ctrl+P → Save as PDF |
| Slow execution | Reduce competitors to 2 for first test run |

---

## 🚀 Next Upgrades

1. **Scheduled runs** — Run weekly automatically with Windows Task Scheduler or cron
2. **Email delivery** — Send report via SendGrid after each run
3. **Diff alerts** — Alert when competitor changes pricing or features
4. **More sources** — Add Google Reviews, LinkedIn, Twitter/X scrapers
5. **Web UI** — Wrap in FastAPI + React for non-technical users
6. **Vector memory** — Store historical reports in Pinecone for trend analysis
