"""Remote management config fetch/cache helpers."""

import json
import time
import urllib.request
from pathlib import Path

from file_utils import load_json, save_json


SCHEMA_VERSION = 1
DEFAULT_MANAGEMENT = {
    "schema_version": SCHEMA_VERSION,
    "version": "local-default",
    "global_stats": {"enabled": True, "message": ""},
    "challenges": {"enabled": False, "replace": False, "manifest": {"version": "none", "challenges": []}},
}


def normalize_management(data):
    if not isinstance(data, dict):
        return dict(DEFAULT_MANAGEMENT)

    clean = dict(DEFAULT_MANAGEMENT)
    clean.update(data)
    clean["schema_version"] = int(clean.get("schema_version") or SCHEMA_VERSION)
    clean["version"] = str(clean.get("version") or "remote")

    global_stats = clean.get("global_stats")
    if not isinstance(global_stats, dict):
        global_stats = {}
    clean["global_stats"] = {
        "enabled": bool(global_stats.get("enabled", True)),
        "message": str(global_stats.get("message", "") or ""),
    }

    challenges = clean.get("challenges")
    if not isinstance(challenges, dict):
        challenges = {}
    manifest = challenges.get("manifest")
    if not isinstance(manifest, dict):
        manifest = {"version": "none", "challenges": []}
    if not isinstance(manifest.get("challenges"), list):
        manifest["challenges"] = []
    clean["challenges"] = {
        "enabled": bool(challenges.get("enabled", False)),
        "replace": bool(challenges.get("replace", False)),
        "manifest": manifest,
    }
    return clean


def load_cached_management(cache_path):
    path = Path(cache_path)
    if not path.exists():
        return dict(DEFAULT_MANAGEMENT)
    try:
        return normalize_management(load_json(path))
    except Exception:
        return dict(DEFAULT_MANAGEMENT)


def fetch_remote_management(url, cache_path, timeout=5):
    if not url:
        return {
            "ok": False,
            "source": "default",
            "management": load_cached_management(cache_path),
            "error": "remote management URL is not configured",
        }

    try:
        request = urllib.request.Request(url, headers={"User-Agent": "BO3TrackerRemoteManagement/3.7"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        management = normalize_management(data)
        management["fetched_at"] = int(time.time())
        save_json(cache_path, management)
        return {"ok": True, "source": "remote", "management": management, "error": ""}
    except Exception as exc:
        return {
            "ok": False,
            "source": "cache",
            "management": load_cached_management(cache_path),
            "error": str(exc),
        }
