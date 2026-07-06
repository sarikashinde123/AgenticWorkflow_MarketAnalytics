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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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


# ── HTML report ────────────────────────────────────────────────
@app.get("/api/pipeline/{run_id}/report", response_class=HTMLResponse)
def get_report(run_id: str, db: Session = Depends(get_db)):
    rec = db.query(RunRecord).filter_by(run_id=run_id).first()
    if not rec or not rec.report_html:
        raise HTTPException(status_code=404, detail="Report not ready")
    return HTMLResponse(content=rec.report_html)


# ── Run history ────────────────────────────────────────────────
@app.get("/api/pipeline/history")
def get_history(db: Session = Depends(get_db)):
    runs = db.query(RunRecord).order_by(RunRecord.created_at.desc()).limit(20).all()
    return [
        {
            "run_id": r.run_id,
            "status": r.status,
            "business_name": (r.input_data or {}).get("business_name", ""),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "report_ready": bool(r.report_html),
        }
        for r in runs
    ]


@app.get("/health")
def health():
    return {"status": "ok"}
