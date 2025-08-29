from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import storage


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def apply_retention_policy(days: int):
    """Delete campaign outputs older than the retention window (in days)."""
    if days <= 0:
        return
    root = f"{storage.get_root()}/outputs"
    try:
        campaigns = storage.list_folder(root)
    except Exception:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for c in campaigns:
        campaign_dir = f"{root}/{c}"
        catalog_path = f"{campaign_dir}/catalog.json"
        created: Optional[datetime] = None
        try:
            cat = storage.read_json(catalog_path)
            ts = cat.get("created_at") or cat.get("ts")
            if ts:
                created = _parse_iso(ts)
        except Exception:
            created = None
        if created and created < cutoff:
            try:
                storage.delete_path(campaign_dir)
                print(f"Governance: deleted campaign {c} due to retention ({days}d)")
            except Exception as e:
                print(f"Governance: failed to delete {campaign_dir}: {e}")

