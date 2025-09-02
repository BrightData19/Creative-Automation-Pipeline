from __future__ import annotations

"""
Creative Automation MCP Server (Python)

Tools:
- list_campaigns() -> list[str]
- list_products(campaign: str) -> list[str]
- get_variants(campaign: str, product: str) -> list[Variant]
- approve(campaign: str, product: str, decision: str = "approved", reviewer: str | None = None) -> dict
- get_alert_context(campaign: str) -> dict
- get_alert_prompt(campaign: str) -> str

Resources:
- alerts/instructions: text guidelines for human-readable alerts

Run:
  uv run python mcp_server.py
"""

import os
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP, Context  # type: ignore

from storage_io import list_folder, get_root, download_bytes, read_json


app = FastMCP("creative-automation-mcp")


def _outputs_dir() -> str:
    return f"{get_root()}/outputs"


def _skip_dirs() -> set[str]:
    return {"finalized", "messages", "carousels", "videos", "approvals", "ingested"}


def _list_dir_names(path: str) -> List[str]:
    names = list_folder(path) or []
    # Some backends include files; we only want directories but we lack stat APIs.
    # Heuristic: keep names without a dot, or those not common file types.
    exts = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".json")
    return [n for n in names if not any(n.lower().endswith(e) for e in exts)]


def _list_files(path: str) -> List[str]:
    names = list_folder(path) or []
    # Heuristic: file names often have a dot
    return [n for n in names if "." in n]


def _read_lineage(dir_rel: str, basename: str) -> Optional[dict]:
    try:
        return read_json(f"{dir_rel}/{basename}.json")
    except Exception:
        return None


@app.tool()
def list_campaigns(ctx: Context) -> List[str]:
    """List available campaign output folders."""
    return _list_dir_names(_outputs_dir())


@app.tool()
def list_products(ctx: Context, campaign: str) -> List[str]:
    """List product slugs for a campaign."""
    product_dir = f"{_outputs_dir()}/{campaign}"
    names = [n for n in _list_dir_names(product_dir) if n not in _skip_dirs()]
    # Render as human-friendly names
    return [n.replace("_", " ") for n in names]


@app.tool()
def get_variants(ctx: Context, campaign: str, product: str) -> List[Dict[str, Any]]:
    """List image variants for a product as objects: {ratio, path, market, compliance_score}."""
    product_slug = product.replace(" ", "_")
    base = f"{_outputs_dir()}/{campaign}/{product_slug}"
    ratios = _list_dir_names(base)
    out: List[Dict[str, Any]] = []
    for r in ratios:
        dir_rel = f"{base}/{r}"
        files = _list_files(dir_rel)
        for f in files:
            if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                continue
            basename = f.rsplit(".", 1)[0]
            lineage = _read_lineage(dir_rel, basename)
            out.append({
                "ratio": r.replace("x", ":"),
                "path": f"dropbox:{dir_rel}/{f}" if os.getenv("STORAGE_BACKEND", "dropbox").lower() == "dropbox" else f"local:{dir_rel}/{f}",
                "target_market": lineage.get("market") if isinstance(lineage, dict) else None,
                "compliance_score": lineage.get("compliance_score") if isinstance(lineage, dict) else None,
            })
    return out


def _get_kafka_producer():  # lazy import to avoid dependency at import-time
    from kafka import KafkaProducer  # type: ignore
    from kafka.errors import NoBrokersAvailable  # type: ignore

    broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    try:
        return KafkaProducer(
            bootstrap_servers=broker,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda v: (v.encode("utf-8") if isinstance(v, str) else v),
        )
    except NoBrokersAvailable as e:  # pragma: no cover - runtime env
        raise RuntimeError(f"Kafka broker not available at {broker}: {e}")


TOPIC_APPROVALS_DECISION = "approvals.decision.v1"


@app.tool()
def approve(ctx: Context, campaign: str, product: str, decision: str = "approved", reviewer: Optional[str] = None) -> Dict[str, Any]:
    """Publish an approval decision to Kafka (approvals.decision.v1). Decision: approved/rejected."""
    d = (decision or "").lower().strip()
    if d not in {"approved", "rejected"}:
        raise ValueError("decision must be 'approved' or 'rejected'")
    event = {
        "event_id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "campaign_name": campaign,
        "product": product,
        "decision": d,
        "reviewer": reviewer or "mcp",
    }
    prod = _get_kafka_producer()
    prod.send(TOPIC_APPROVALS_DECISION, event)
    prod.flush(timeout=5)
    return {"ok": True, "event": event}


def _collect_campaign_stats(campaign: str) -> Dict[str, Any]:
    outputs = _outputs_dir()
    product_root = f"{outputs}/{campaign}"
    prods = [n for n in _list_dir_names(product_root) if n not in _skip_dirs()]
    total_variants = 0
    avg_compliance = 0.0
    scores: List[float] = []
    by_product: Dict[str, Any] = {}
    for slug in prods:
        ratios = _list_dir_names(f"{product_root}/{slug}")
        items = 0
        for r in ratios:
            files = _list_files(f"{product_root}/{slug}/{r}")
            for f in files:
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                    items += 1
                    basename = f.rsplit(".", 1)[0]
                    lineage = _read_lineage(f"{product_root}/{slug}/{r}", basename)
                    if isinstance(lineage, dict) and isinstance(lineage.get("compliance_score"), (int, float)):
                        scores.append(float(lineage["compliance_score"]))
        by_product[slug.replace("_", " ")] = {"variants": items}
        total_variants += items
    avg_compliance = (sum(scores) / len(scores)) if scores else 0.0
    return {
        "campaign": campaign,
        "products": list(by_product.keys()),
        "products_count": len(by_product),
        "variants_count": total_variants,
        "avg_compliance": avg_compliance,
        "by_product": by_product,
    }


@app.tool()
def get_alert_context(ctx: Context, campaign: str) -> Dict[str, Any]:
    """Return structured context for composing a human-readable alert for a campaign."""
    stats = _collect_campaign_stats(campaign)
    # Optionally include a recent compliance report if present in outputs/<campaign>/finalized manifests
    try:
        cat = read_json(f"{_outputs_dir()}/{campaign}/catalog.json")
    except Exception:
        cat = None
    brand_name = None
    if isinstance(cat, dict):
        brand_name = cat.get("brand_name") or cat.get("brand")
    payload = {
        "campaign": stats["campaign"],
        "brand_name": brand_name,
        "issue": "quality_review",  # default placeholder; caller can refine
        "impact": f"Generated {stats['variants_count']} variants across {stats['products_count']} products.",
        "suggested_next_steps": "Review low-scoring items, re-generate where needed, and proceed to approvals.",
        "target_audience": ["marketing_ops", "brand_safety"],
        "context": {
            "avg_compliance": stats["avg_compliance"],
            "by_product": stats["by_product"],
            "catalog": cat,
        },
    }
    return payload


@app.tool()
def get_alert_prompt(ctx: Context, campaign: str) -> str:
    """Return a deterministic prompt string for the LLM, embedding the MCP context payload."""
    mcp_payload = get_alert_context(ctx, campaign)
    mcp_json = json.dumps(mcp_payload, indent=2)
    instructions = ALERT_INSTRUCTIONS.strip()
    return f"{instructions}\n\nMCP:\n{mcp_json}\n"


ALERT_INSTRUCTIONS = """
You are the Alert Draft assistant for the Creative Automation pipeline.

Write a concise, human-readable alert for internal stakeholders with:
- Title: Campaign + issue summary (one line)
- Summary: 2–3 sentences stating context, key metrics, and impact
- Key Stats: products count, variants count, avg compliance (as %)
- Actions: 2–3 bullet next steps tailored to stakeholders

Tone: factual, calm, and actionable. Avoid marketing fluff.
Audience: marketing_ops and brand_safety.
"""


@app.resource("mcp://alerts/instructions")
def alerts_instructions() -> str:
    """Human-in-the-loop alert drafting guidelines used by the LLM."""
    return ALERT_INSTRUCTIONS


if __name__ == "__main__":
    # Run MCP over stdio (default transport for MCP tooling)
    app.run()
