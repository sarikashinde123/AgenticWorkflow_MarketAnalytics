"""
Celery task — runs the full 5-agent pipeline asynchronously.
Publishes SSE events to Redis pub/sub so FastAPI can stream them to the browser.
"""
from __future__ import annotations
import json
from datetime import datetime
import redis

from config import settings
from tasks.celery_app import celery_app
from db.database import SessionLocal, RunRecord
from agents import agent0_discovery, agent1_scraper_gen, agent2_scraper, agent3_analyst, agent4_report

# Keepalive + auto-retry so a connection that goes idle between agents
# (common through Docker's WSL relay on Windows) doesn't fail the next publish.
r = redis.from_url(
    settings.redis_url,
    socket_keepalive=True,
    retry_on_timeout=True,
    health_check_interval=30,
)

AGENTS_META = [
    {"id": 0, "label": "Agent 0 — Business Discovery",  "model": "claude-sonnet-4-6"},
    {"id": 1, "label": "Agent 1 — Scraper Generator",   "model": "claude-opus-4-8"},
    {"id": 2, "label": "Agent 2 — Website Scraper",     "model": "claude-haiku-4-5-20251001"},
    {"id": 3, "label": "Agent 3 — Deep Analyst",        "model": "claude-opus-4-8"},
    {"id": 4, "label": "Agent 4 — Report Writer",       "model": "claude-opus-4-8"},
]


def _pub(run_id: str, event: str, data: dict):
    """Publish an SSE event to Redis pub/sub channel.

    Best-effort: a live-progress broadcast must never crash the pipeline.
    The report is persisted to the DB regardless, so a dropped token or even
    a dropped 'pipeline_done' event is recoverable via the /report endpoint.
    """
    payload = json.dumps({"event": event, **data})
    try:
        r.publish(f"pipeline:{run_id}", payload)
    except Exception:
        pass


def _update_db(run_id: str, **kwargs):
    db = SessionLocal()
    try:
        rec = db.query(RunRecord).filter_by(run_id=run_id).first()
        if rec:
            for k, v in kwargs.items():
                setattr(rec, k, v)
            db.commit()
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.pipeline_task.run_pipeline")
def run_pipeline(self, run_id: str, input_data: dict):
    try:
        _pub(run_id, "pipeline_start", {"run_id": run_id})
        _update_db(run_id, status="running")

        business_name     = input_data["business_name"]
        business_type     = input_data["business_type"]
        location          = input_data["location"]
        search_radius_km  = input_data["search_radius_km"]

        # ── Agent 0 ──────────────────────────────────────────────
        _pub(run_id, "agent_start", {"agent_id": 0, "agent_label": AGENTS_META[0]["label"]})

        def tok0(t): _pub(run_id, "agent_token", {"agent_id": 0, "data": t})

        input_schema = agent0_discovery.run(
            business_name, business_type, location, search_radius_km, on_token=tok0
        )
        _pub(run_id, "agent_done", {"agent_id": 0, "data": json.dumps(input_schema)[:200]})

        # ── Agent 1 ──────────────────────────────────────────────
        _pub(run_id, "agent_start", {"agent_id": 1, "agent_label": AGENTS_META[1]["label"]})

        def tok1(t): _pub(run_id, "agent_token", {"agent_id": 1, "data": t})

        scraper_scripts = agent1_scraper_gen.run(input_schema, on_token=tok1)
        _pub(run_id, "agent_done", {"agent_id": 1, "data": f"{len(scraper_scripts)} scripts generated"})

        # ── Agent 2 ──────────────────────────────────────────────
        _pub(run_id, "agent_start", {"agent_id": 2, "agent_label": AGENTS_META[2]["label"]})

        def tok2(t): _pub(run_id, "agent_token", {"agent_id": 2, "data": t})

        raw_data = agent2_scraper.run(scraper_scripts, on_token=tok2)
        _pub(run_id, "agent_done", {"agent_id": 2, "data": f"{len(raw_data)} competitors scraped"})

        # ── Agent 3 ──────────────────────────────────────────────
        _pub(run_id, "agent_start", {"agent_id": 3, "agent_label": AGENTS_META[3]["label"]})

        def tok3(t): _pub(run_id, "agent_token", {"agent_id": 3, "data": t})

        analysis = agent3_analyst.run(input_schema, raw_data, on_token=tok3)
        _pub(run_id, "agent_done", {"agent_id": 3, "data": analysis.get("executive_summary", "")[:200]})

        # ── Agent 4 ──────────────────────────────────────────────
        _pub(run_id, "agent_start", {"agent_id": 4, "agent_label": AGENTS_META[4]["label"]})

        html_chunks: list[str] = []

        def tok4(t):
            html_chunks.append(t)
            _pub(run_id, "agent_token", {"agent_id": 4, "data": t})

        agent4_report.run(input_schema, analysis, on_chunk=tok4)
        report_html = "".join(html_chunks)

        _pub(run_id, "agent_done", {"agent_id": 4, "data": f"Report generated ({len(report_html):,} chars)"})

        # ── PDF conversion via ReportLab ─────────────────────────
        pdf_url = _convert_to_pdf(run_id, report_html)

        # ── Finalise ──────────────────────────────────────────────
        _update_db(
            run_id,
            status="completed",
            report_html=report_html,
            pdf_url=pdf_url,
            completed_at=datetime.utcnow(),
        )
        _pub(run_id, "pipeline_done", {"run_id": run_id, "pdf_url": pdf_url})

    except Exception as exc:
        _update_db(run_id, status="failed", error=str(exc))
        _pub(run_id, "error", {"message": str(exc)})
        raise


def _register_unicode_font():
    """Register a Unicode TTF (with ₹ and ✓/✗/★) if one is on the system.

    Returns (regular_name, bold_name, unicode_ok). Falls back to Helvetica.
    """
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        (r"C:\Windows\Fonts\arial.ttf",   r"C:\Windows\Fonts\arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ]
    for regular, bold in candidates:
        if not os.path.exists(regular):
            continue
        try:
            pdfmetrics.registerFont(TTFont("RB", regular))
            pdfmetrics.registerFont(TTFont("RBB", bold if os.path.exists(bold) else regular))
            pdfmetrics.registerFontFamily("RB", normal="RB", bold="RBB", italic="RB", boldItalic="RBB")
            return "RB", "RBB", True
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold", False


def _convert_to_pdf(run_id: str, html: str) -> str | None:
    """
    Convert the HTML report to a PDF that preserves its structure.

    Walks the DOM (BeautifulSoup) so text inside <div> cards isn't dropped,
    renders <table> as real tables, and uses a Unicode font so ₹ renders.
    Saves to settings.reports_dir and returns a relative URL served by FastAPI.
    """
    import os
    import re
    from bs4 import BeautifulSoup, Tag
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    from config import settings

    reports_dir = settings.reports_dir
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"report_{run_id}.pdf")

    FONT, FONT_B, unicode_ok = _register_unicode_font()

    # Tags whose presence in a subtree means "recurse", not "treat as one block".
    STRUCTURAL = {"div", "section", "article", "main", "header", "footer",
                  "ul", "ol", "table", "p", "li", "blockquote",
                  "h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP = {"script", "style", "head", "meta", "link", "br", "hr", "img", "svg", "nav"}

    def esc(t: str) -> str:
        if not unicode_ok:
            t = t.replace("₹", "Rs ")   # ₹ -> "Rs " when the font lacks the glyph
        # Drop decorative glyphs most system fonts render as tofu (□). The data
        # they carried (star ratings, ✓/✗) is conveyed as text/numbers instead.
        for ch in ("★", "☆", "✓", "✗", "✔", "✘", "▲", "▼", "◉", "●", "½"):
            t = t.replace(ch, "")
        t = t.strip()
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def meaningful(t: str) -> bool:
        # Drop bare visual labels like a progress-bar's "9" or a stray "•".
        return bool(t) and len(t) > 2

    try:
        soup = BeautifulSoup(html, "html.parser")

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
            title="Competitive Intelligence Report",
        )
        avail = doc.width

        ink = colors.HexColor("#181b22")
        accent = colors.HexColor("#4338ca")
        muted = colors.HexColor("#4b5563")

        style_h1 = ParagraphStyle("H1", fontName=FONT_B, fontSize=20, textColor=ink, spaceAfter=6, leading=24)
        style_h2 = ParagraphStyle("H2", fontName=FONT_B, fontSize=14, textColor=accent, spaceBefore=16, spaceAfter=8, leading=18)
        style_h3 = ParagraphStyle("H3", fontName=FONT_B, fontSize=11.5, textColor=ink, spaceBefore=8, spaceAfter=5, leading=15)
        style_body = ParagraphStyle("Body", fontName=FONT, fontSize=9.5, textColor=colors.HexColor("#2b3038"), spaceAfter=6, leading=14)
        style_li = ParagraphStyle("Li", parent=style_body, leftIndent=12)
        th_style = ParagraphStyle("TH", fontName=FONT_B, fontSize=8, textColor=accent, leading=10)
        td_style = ParagraphStyle("TD", fontName=FONT, fontSize=8.5, textColor=ink, leading=11)
        yes_style = ParagraphStyle("YES", parent=td_style, textColor=colors.HexColor("#16a34a"), fontName=FONT_B, alignment=1)
        no_style = ParagraphStyle("NO", parent=td_style, textColor=colors.HexColor("#dc2626"), fontName=FONT_B, alignment=1)

        flow = []

        def add_para(text, style, bullet=False):
            t = (text or "").strip()
            if not meaningful(t):
                return
            flow.append(Paragraph(("• " if bullet else "") + esc(t), style))

        def cell_text(c) -> str:
            return c.get_text(" ", strip=True)

        def build_table(table_el):
            thead = table_el.find("thead")
            header_cells = thead.find_all(["th", "td"]) if thead else []
            body_scope = table_el.find("tbody") or table_el
            rows = []
            for tr in body_scope.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if cells:
                    rows.append((tr, cells))
            if not header_cells and rows:
                header_cells = rows[0][1]
                rows = rows[1:]
            ncol = max([len(header_cells)] + [len(c) for _, c in rows] or [0])
            if ncol == 0:
                return None

            # Column widths proportional to average text length (min floor).
            lens = [[] for _ in range(ncol)]
            for i, c in enumerate(header_cells[:ncol]):
                lens[i].append(len(cell_text(c)))
            for _, cells in rows:
                for i, c in enumerate(cells[:ncol]):
                    lens[i].append(len(cell_text(c)))
            import math
            avgs = [(sum(l) / len(l)) if l else 4.0 for l in lens]
            weights = [math.sqrt(max(2.0, a)) for a in avgs]   # soften Notes dominance
            min_w = 1.9 * cm                                    # floor so no column wraps letter-by-letter
            remaining = max(0.0, avail - min_w * ncol)
            tw = sum(weights) or 1.0
            col_widths = [min_w + remaining * w / tw for w in weights]

            def mk(c, header=False):
                txt = cell_text(c)
                st = th_style if header else td_style
                disp = txt
                if not header and txt in ("✓", "✔"):
                    st, disp = yes_style, "Yes"
                elif not header and txt in ("✗", "✘", "×"):
                    st, disp = no_style, "No"
                return Paragraph(esc(disp) or "&nbsp;", st)

            data = [[mk(c, True) for c in header_cells[:ncol]] + [Paragraph("", th_style)] * (ncol - len(header_cells))]
            our_rows = []
            for r_idx, (tr, cells) in enumerate(rows, start=1):
                data.append([mk(c) for c in cells[:ncol]] + [Paragraph("", td_style)] * (ncol - len(cells)))
                if "our" in " ".join(tr.get("class") or []):
                    our_rows.append(r_idx)

            tbl = Table(data, colWidths=col_widths, repeatRows=1)
            ts = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#c7d2fe")),
                ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ]
            for r in our_rows:
                ts.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#eef2ff")))
            tbl.setStyle(TableStyle(ts))
            return tbl

        def render(el):
            for child in el.children:
                if not isinstance(child, Tag):
                    continue
                name = (child.name or "").lower()
                if name in SKIP:
                    continue
                if name == "table":
                    t = build_table(child)
                    if t is not None:
                        flow.append(t)
                        flow.append(Spacer(1, 10))
                    continue
                if name == "h1":
                    add_para(child.get_text(" ", strip=True), style_h1)
                    flow.append(HRFlowable(width="100%", thickness=1.2, color=accent, spaceAfter=8))
                    continue
                if name == "h2":
                    add_para(child.get_text(" ", strip=True), style_h2)
                    continue
                if name in ("h3", "h4", "h5", "h6"):
                    add_para(child.get_text(" ", strip=True), style_h3)
                    continue
                if name == "li":
                    add_para(child.get_text(" ", strip=True), style_li, bullet=True)
                    continue
                if name == "p":
                    add_para(child.get_text(" ", strip=True), style_body)
                    continue
                # container vs leaf: recurse only if it wraps structural blocks
                has_struct = any(
                    isinstance(d, Tag) and (d.name or "").lower() in STRUCTURAL
                    for d in child.descendants
                )
                if has_struct:
                    render(child)
                else:
                    add_para(child.get_text(" ", strip=True), style_body)

        render(soup.body or soup)

        if not flow:
            flow.append(Paragraph("Intelligence Report", style_h1))
            flow.append(Paragraph(esc(soup.get_text(" ", strip=True)[:3000]), style_body))

        doc.build(flow)
        return f"/reports/report_{run_id}.pdf"

    except Exception as e:
        import traceback
        print(f"[PDF] conversion error: {e}\n{traceback.format_exc()}")
        return None
