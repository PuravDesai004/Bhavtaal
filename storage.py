"""AI-only audio persistence for Embarko storage or local development."""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

from config import app_name, data_dir

logger = logging.getLogger(__name__)
LOCAL_AUDIO_LIMIT = 300


def _safe_filename(deal_id: str) -> str:
    safe = "".join(char for char in deal_id if char.isalnum() or char in "-_")
    if not safe or safe != deal_id:
        raise ValueError("invalid deal id")
    return f"deal-{safe}.wav"


def _mtime_or_zero(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _prune_local_audio(audio_dir: Path) -> None:
    files = sorted(
        (path for path in audio_dir.glob("deal-*.wav") if path.is_file()),
        key=_mtime_or_zero,
        reverse=True,
    )
    for old_file in files[LOCAL_AUDIO_LIMIT:]:
        try:
            old_file.unlink()
        except OSError as exc:
            logger.warning("Local audio prune failed (%s)", type(exc).__name__)


def _list_prunable(client: Any, base: str, headers: dict[str, str]) -> list[tuple[str, str]]:
    response = client.get(f"{base}/apps/{quote(app_name(), safe='')}/files", headers=headers)
    if response.status_code >= 400:
        return []
    try:
        payload: Any = response.json()
    except ValueError:
        return []
    entries = payload.get("files", payload) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return []
    files = []
    for item in entries:
        if not isinstance(item, dict) or item.get("pinned") is True:
            continue
        name = str(item.get("filename") or item.get("name") or "")
        basename = name.rsplit("/", 1)[-1]
        if basename.startswith("deal-") and basename.lower().endswith(".wav"):
            files.append((item, basename))
    files.sort(key=lambda pair: str(pair[0].get("createdAt") or pair[0].get("created_at") or pair[0].get("uploaded_at") or pair[0].get("created") or ""))
    return [(str(item.get("id") or item.get("file_id") or name), name) for item, name in files[:5]]


def _prune_file(client: Any, base: str, name: str, file_id: str, headers: dict[str, str]) -> bool:
    candidates: list[str] = []
    if file_id:
        candidates.append(file_id)
    if name and name not in candidates:
        candidates.append(name)
    for candidate in candidates:
        try:
            response = client.delete(f"{base}/{quote(candidate, safe='')}", headers=headers)
            if response.status_code < 400:
                return True
        except Exception as exc:
            logger.warning("Embarko audio prune failed (%s)", type(exc).__name__)
    logger.warning("Embarko audio prune failed for %s", name or file_id)
    return False


def persist_ai_audio(deal_id: str, wav_bytes: bytes | None) -> str | None:
    """Save only a generated boss reaction. User recordings never reach this module."""
    if not wav_bytes or not wav_bytes.startswith(b"RIFF") or b"WAVE" not in wav_bytes[:16]:
        return None
    filename = _safe_filename(deal_id)
    storage_url = os.environ.get("STORAGE_URL", "").rstrip("/")
    token = os.environ.get("STORAGE_TOKEN", "")
    if not storage_url or not token:
        audio_dir = data_dir() / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        path = audio_dir / filename
        path.write_bytes(wav_bytes)
        _prune_local_audio(audio_dir)
        return f"/api/local-audio/{quote(deal_id, safe='')}"

    import httpx

    base = f"{storage_url}/apps/{quote(app_name(), safe='')}/files"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "audio/wav",
        "Content-Length": str(len(wav_bytes)),
    }
    with httpx.Client(timeout=12.0) as client:
        response = client.put(f"{base}/{quote(filename, safe='')}", content=wav_bytes, headers=headers)
        if response.status_code == 409:
            auth_headers = {"Authorization": f"Bearer {token}"}
            for old_id, old_name in _list_prunable(client, storage_url, auth_headers):
                _prune_file(client, base, old_name, old_id, auth_headers)
            response = client.put(f"{base}/{quote(filename, safe='')}", content=wav_bytes, headers=headers)
        if response.status_code >= 400:
            logger.warning("Embarko audio upload failed (HTTP %s)", response.status_code)
            response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        public_url = (payload.get("url") or payload.get("public_url") or payload.get("publicUrl")) if isinstance(payload, dict) else None
        if not public_url:
            raise ValueError("Embarko storage did not return a public file URL")
        return str(public_url)


def local_audio_path(deal_id: str) -> Path | None:
    try:
        path = data_dir() / "audio" / _safe_filename(deal_id)
    except ValueError:
        return None
    return path if path.is_file() else None
