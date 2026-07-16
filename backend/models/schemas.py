from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class PipelineStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class AgentStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class PipelineMode(str, Enum):
    market_overview = "market_overview"   # new business — survey competitor offerings
    gap_analysis = "gap_analysis"          # existing business — compare own offerings vs market


# ── Input ──────────────────────────────────────────────────────
class PipelineInput(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=100)
    business_type: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=2, max_length=200)
    search_radius_km: int = Field(default=5, ge=1, le=50)
    max_competitors: int = Field(default=6, ge=3, le=15)
    use_opus: bool = Field(default=False)
    strict_match: bool = Field(default=False)
    mode: PipelineMode = PipelineMode.market_overview
    # In gap_analysis mode, the user's own offerings (extracted from their PDF).
    own_offerings: Optional[str] = Field(default=None, max_length=20000)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


# ── Business / Competitor schema ───────────────────────────────
class CompetitorInfo(BaseModel):
    name: str
    website: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    priority: str = "medium"
    notes: Optional[str] = None


class InputSchema(BaseModel):
    business: dict
    competitors: List[CompetitorInfo]
    search_radius_km: int
    location: str


# ── Agent run state ────────────────────────────────────────────
class AgentRun(BaseModel):
    agent_id: int
    label: str
    model: str
    status: AgentStatus = AgentStatus.pending
    output_preview: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ── Pipeline run ───────────────────────────────────────────────
class PipelineRun(BaseModel):
    run_id: str
    status: PipelineStatus = PipelineStatus.pending
    input: PipelineInput
    agents: List[AgentRun] = []
    report_html: Optional[str] = None
    report_pdf_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# ── SSE event ─────────────────────────────────────────────────
class SSEEvent(BaseModel):
    event: str          # agent_start | agent_token | agent_done | pipeline_done | error
    agent_id: Optional[int] = None
    agent_label: Optional[str] = None
    data: Any = None


# ── API responses ──────────────────────────────────────────────
class StartResponse(BaseModel):
    run_id: str
    message: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: PipelineStatus
    agents: List[AgentRun]
    report_ready: bool
    pdf_url: Optional[str] = None
