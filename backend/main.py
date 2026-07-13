"""
FastAPI backend — Competitive Intelligence Pipeline
Routes:
  POST /api/pipeline/start       → start pipeline, return run_id
  GET  /api/pipeline/{id}/stream → SSE stream of agent events
  GET  /api/pipeline/{id}/status → current run status
  GET  /api/pipeline/{id}/report → final HTML report
  GET  /api/pipeline/history     → list past runs
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator

import io
import os
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from config import settings
from db.database import init_db, get_db, RunRecord, SessionLocal
from models.schemas import PipelineInput, StartResponse, RunStatusResponse, PipelineStatus
from tasks.celery_app import celery_app  # noqa — registers tasks
from tasks.pipeline_task import run_pipeline

app = FastAPI(title="Competitor Intel API", version="1.0.0")

# Allowed browser origins. Comma-separated env var in production
# (e.g. ALLOWED_ORIGINS="https://myapp.up.railway.app"); defaults to localhost.
_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


os.makedirs(settings.reports_dir, exist_ok=True)


@app.on_event("startup")
def startup():
    init_db()

# Serve generated PDF files
app.mount("/reports", StaticFiles(directory=settings.reports_dir), name="reports")


# ── Extract offerings from an uploaded PDF (Gap Analysis mode) ──
@app.post("/api/offerings/extract")
async def extract_offerings(file: UploadFile = File(...)):
    """Read the user's own-offerings PDF and return its text for gap analysis."""
    name = (file.filename or "").lower()
    if not name.endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF is too large (max 10 MB).")

    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read the PDF: {exc}")

    if not text:
        raise HTTPException(
            status_code=400,
            detail="No readable text found — the PDF looks scanned or image-only.",
        )

    return {"text": text[:20000], "chars": len(text), "pages": len(reader.pages),
            "filename": file.filename}


# ── Start pipeline ─────────────────────────────────────────────
@app.post("/api/pipeline/start", response_model=StartResponse)
def start_pipeline(body: PipelineInput, db: Session = Depends(get_db)):
    run_id = str(uuid.uuid4())

    record = RunRecord(
        run_id=run_id,
        status="pending",
        input_data=body.model_dump(),
        agents=[],
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()

    # Dispatch Celery task
    run_pipeline.apply_async(
        args=[run_id, body.model_dump()],
        task_id=run_id,
    )

    return StartResponse(run_id=run_id, message="Pipeline started")


# ── SSE stream ─────────────────────────────────────────────────
@app.get("/api/pipeline/{run_id}/stream")
async def stream_pipeline(run_id: str):
    """
    Server-Sent Events endpoint.
    Subscribes to Redis pub/sub channel pipeline:{run_id}
    and forwards every event to the browser.
    """
    async def event_generator() -> AsyncGenerator:
        redis_client = aioredis.from_url(settings.redis_url)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"pipeline:{run_id}")

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                raw = message["data"]
                if isinstance(raw, bytes):
                    raw = raw.decode()
                try:
                    data = json.loads(raw)
                except Exception:
                    continue

                event_type = data.pop("event", "message")
                yield {"event": event_type, "data": json.dumps(data)}

                # Stop streaming once pipeline finishes
                if event_type in ("pipeline_done", "error"):
                    break
        finally:
            await pubsub.unsubscribe(f"pipeline:{run_id}")
            await redis_client.aclose()

    return EventSourceResponse(event_generator())


# ── Run status ─────────────────────────────────────────────────
@app.get("/api/pipeline/{run_id}/status", response_model=RunStatusResponse)
def get_status(run_id: str, db: Session = Depends(get_db)):
    rec = db.query(RunRecord).filter_by(run_id=run_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatusResponse(
        run_id=run_id,
        status=PipelineStatus(rec.status),
        agents=rec.agents or [],
        report_ready=bool(rec.report_html),
        pdf_url=rec.pdf_url,
    )


# ── Competitor map data ────────────────────────────────────────
@app.get("/api/pipeline/{run_id}/competitors")
def get_competitors(run_id: str, db: Session = Depends(get_db)):
    rec = db.query(RunRecord).filter_by(run_id=run_id).first()
    if not rec or not rec.competitors:
        raise HTTPException(status_code=404, detail="Competitors not ready")
    return rec.competitors


# ── HTML report ────────────────────────────────────────────────
@app.get("/api/pipeline/{run_id}/report", response_class=HTMLResponse)
def get_report(run_id: str, db: Session = Depends(get_db)):
    rec = db.query(RunRecord).filter_by(run_id=run_id).first()
    if not rec or not rec.report_html:
        raise HTTPException(status_code=404, detail="Report not ready")
    return HTMLResponse(content=rec.report_html)


# ── Run history ────────────────────────────────────────────────
@app.get("/api/pipeline/history")
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    runs = db.query(RunRecord).order_by(RunRecord.created_at.desc()).limit(limit).all()
    result = []
    for r in runs:
        inp = r.input_data or {}
        agents = r.agents or []
        total_in = sum(a.get("tokens_in", 0) or 0 for a in agents)
        total_out = sum(a.get("tokens_out", 0) or 0 for a in agents)
        duration = None
        if r.created_at and r.completed_at:
            duration = int((r.completed_at - r.created_at).total_seconds())
        result.append({
            "run_id": r.run_id,
            "status": r.status,
            "business_name": inp.get("business_name", ""),
            "business_type": inp.get("business_type", ""),
            "location": inp.get("location", ""),
            "mode": inp.get("mode", "market_overview"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "duration_seconds": duration,
            "tokens_in": total_in,
            "tokens_out": total_out,
            "tokens_total": total_in + total_out,
            "report_ready": bool(r.report_html),
            "pdf_url": r.pdf_url,
            "error": r.error,
        })
    return result


# ── Geocoding proxy (Photon primary, Nominatim fallback) ──────
_geocode_cache: dict[str, list] = {}

@app.get("/api/geocode")
async def geocode(q: str, limit: int = 5):
    import httpx
    cache_key = f"{q.strip().lower()}:{limit}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Primary: Photon (free, OSM-based, no aggressive rate limiting)
            r = await client.get(
                "https://photon.komoot.io/api/",
                params={"q": q, "limit": limit, "lang": "en"},
            )
            if r.status_code == 200:
                features = r.json().get("features", [])
                data = []
                for f in features:
                    props = f.get("properties", {})
                    coords = f.get("geometry", {}).get("coordinates", [])
                    parts = [props.get("name", "")]
                    for key in ("city", "state", "country"):
                        v = props.get(key, "")
                        if v and v != parts[0]:
                            parts.append(v)
                    data.append({
                        "display_name": ", ".join(p for p in parts if p),
                        "lat": str(coords[1]) if len(coords) >= 2 else "0",
                        "lon": str(coords[0]) if len(coords) >= 2 else "0",
                        "place_id": props.get("osm_id", 0),
                    })
                _geocode_cache[cache_key] = data
                return data

            # Fallback: Nominatim
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"format": "json", "q": q, "limit": limit, "addressdetails": 0},
                headers={"User-Agent": "GeoScout/1.0 (sarikas@incubxperts.com)", "Accept-Language": "en"},
            )
            if r.status_code == 200:
                data = r.json()
                _geocode_cache[cache_key] = data
                return data
            return []
    except Exception:
        return []


@app.get("/health")
def health():
    return {"status": "ok"}
