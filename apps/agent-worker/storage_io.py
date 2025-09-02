"""
Minimal storage adapter for the Agent MCP server.

Supports Dropbox and Local backends to browse outputs and read JSON/bytes.
"""
from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PIL import Image  # noqa: F401  # kept for parity if needed

BACKEND = (os.getenv("STORAGE_BACKEND", "dropbox").lower())

# --- Local backend ---
LOCAL_ROOT = os.getenv("LOCAL_ROOT", "local_storage")


def _abs_local(rel_or_abs: str) -> Path:
    p = rel_or_abs.lstrip("/")
    return Path(LOCAL_ROOT) / p


def ensure_folder(path: str):
    if BACKEND == "local":
        _abs_local(path).mkdir(parents=True, exist_ok=True)


def write_json(path: str, obj: dict):
    if BACKEND == "local":
        fp = _abs_local(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    else:
        raise NotImplementedError("write_json not supported on dropbox in agent storage_io")


def read_json(path: str) -> dict:
    if BACKEND == "local":
        fp = _abs_local(path)
        return json.loads(fp.read_text(encoding="utf-8"))
    else:
        import dropbox  # type: ignore
        from dropbox.exceptions import ApiError  # type: ignore

        dbx = _get_dbx()
        try:
            _, res = dbx.files_download(_normalize_path(path))
            return json.loads(res.content)
        except ApiError as e:  # pragma: no cover - best effort
            raise FileNotFoundError(str(e))


def list_folder(path: str) -> List[str]:
    if BACKEND == "local":
        fp = _abs_local(path)
        if not fp.exists():
            return []
        return [p.name for p in fp.iterdir()]
    else:
        dbx = _get_dbx()
        try:
            result = dbx.files_list_folder(_normalize_path(path))
            return [entry.name for entry in result.entries]
        except Exception:
            return []


def download_bytes(path: str) -> bytes:
    if BACKEND == "local":
        return _abs_local(path).read_bytes()
    else:
        dbx = _get_dbx()
        _, res = dbx.files_download(_normalize_path(path))
        return res.content


def get_root() -> str:
    if BACKEND == "local":
        return LOCAL_ROOT
    root = os.getenv("DROPBOX_ROOT", "/Apps/CreativeAutomation")
    root = "/" + root.lstrip("/")
    if len(root) > 1 and root.endswith("/"):
        root = root[:-1]
    return root


# --- Dropbox helpers ---
_DBX = None


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    p = "/" + path.lstrip("/")
    while "//" in p:
        p = p.replace("//", "/")
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p


def _get_dbx():
    global _DBX
    if _DBX is not None:
        return _DBX
    import dropbox  # type: ignore

    _DBX = dropbox.Dropbox(
        oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
        app_key=os.getenv("DROPBOX_APP_KEY"),
        app_secret=os.getenv("DROPBOX_APP_SECRET"),
    )
    return _DBX

