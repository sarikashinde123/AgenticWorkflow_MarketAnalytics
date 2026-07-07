# RECON — Competitive Intelligence Pipeline

A 5-agent Claude pipeline that researches local competitors and produces a strategic
report. Runs in two modes:

- **Market Overview** — scope competitor offerings for a new business.
- **Gap Analysis** — upload a PDF of your own offerings; the pipeline compares them
  against the market and reports concrete gaps + an action plan.

## Stack

| Part | Tech |
|---|---|
| Frontend | Next.js 15 (recon-terminal UI) |
| Backend API | FastAPI |
| Background pipeline | Celery worker |
| Message broker + live SSE | Redis |
| Storage | PostgreSQL |
| Models | Claude Opus 4.8 / Sonnet 4.6 / Haiku 4.5 (native `web_search`) |

The 5 agents: **0** Discovery → **1** Scraper-generator → **2** Web scraper →
**3** Deep analyst → **4** Report writer (HTML → PDF via ReportLab).

## Run locally

Redis + Postgres come up in Docker; the app runs natively for fast reloads.

```bash
# 1. Infra
docker compose up -d db redis

# 2. Config — copy and fill in your Anthropic key
cp .env.example .env      # set ANTHROPIC_API_KEY

# 3. Backend API
cd backend && pip install -r requirements.txt
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/compintel \
REDIS_URL=redis://localhost:6379/0 \
  uvicorn main:app --reload --port 8000

# 4. Worker (new terminal, same env vars)
cd backend && celery -A tasks.celery_app worker --loglevel=info   # add --pool=solo on Windows

# 5. Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:3000.

Or run the whole stack in Docker: `docker compose up --build`.

## Deploy (Railway) + CI/CD

**Branches:** `main` → staging, `Prod` → production.

**CI (GitHub Actions):** [`.github/workflows/ci.yml`](.github/workflows/ci.yml) builds the
frontend and validates the backend on every push/PR to `main` and `Prod`.

**CD (Railway native):** connect the repo once; Railway auto-deploys on every push.

### One-time Railway setup

1. **railway.app** → New Project → **Deploy from GitHub repo** → pick this repo.
2. Add plugins: **+ New → Database → PostgreSQL**, then **+ New → Database → Redis**.
3. Create three services from the repo (**+ New → GitHub Repo** each time):

   | Service | Root dir | Start command | Key env vars |
   |---|---|---|---|
   | **api** | `backend` | `uvicorn main:app --host 0.0.0.0 --port $PORT` | `ANTHROPIC_API_KEY`, `DATABASE_URL=${{Postgres.DATABASE_URL}}`, `REDIS_URL=${{Redis.REDIS_URL}}`, `ALLOWED_ORIGINS=<frontend URL>` |
   | **worker** | `backend` | `celery -A tasks.celery_app worker --loglevel=info` | same as api (no `ALLOWED_ORIGINS` needed) |
   | **frontend** | `frontend` | (auto — Next.js) | `NEXT_PUBLIC_API_URL=<api public URL>` |

4. In each service: **Settings → Environment → Production branch = `Prod`** (staging service can track `main`).
5. Generate a public domain for **api** and **frontend** (Settings → Networking). Then set
   `NEXT_PUBLIC_API_URL` (frontend) and `ALLOWED_ORIGINS` (api) to those URLs and redeploy.

See [`.env.production.example`](.env.production.example) for the full variable list.

### The flow

```
push to main  → CI runs → Railway deploys staging
push to Prod  → CI runs → Railway deploys production
```

Promote staging to production with: `git checkout Prod && git merge main && git push`.
