"""Remote sync helper for the custom camo database."""

import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.request

from app_paths import get_base_path
from game_data import CAMO_DB_FILE

CUSTOM_CAMOS_URL = "https://uemmaps.com/custom_camos.json"
DEFAULT_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


def _camo_db_path():
    return os.path.join(get_base_path(), CAMO_DB_FILE)


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_local_hash(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return _sha256_text(handle.read())
    except Exception:
        return ""


def _validate_camo_payload(text):
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Remote custom_camos.json must contain a list.")
    for index, item in enumerate(data[:20]):
        if not isinstance(item, dict):
            raise ValueError(f"Camo entry {index + 1} must be an object.")
        if "id" not in item or "name" not in item:
            raise ValueError(f"Camo entry {index + 1} is missing id or name.")
    return data


def _open_request_with_tls_fallback(request):
    try:
        return urllib.request.urlopen(request, timeout=10), False
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLError):
            context = ssl._create_unverified_context()
            return urllib.request.urlopen(request, timeout=10, context=context), True
        raise


def sync_custom_camos(app_config, force=False, interval_seconds=DEFAULT_CHECK_INTERVAL_SECONDS):
    now = int(time.time())
    last_check = int(app_config.get("custom_camos_last_check", 0) or 0)
    if not force and last_check and now - last_check < interval_seconds:
        return {
            "ok": True,
            "skipped": True,
            "reason": "rate_limited_locally",
            "msg": "Custom camos sync skipped: recently checked.",
        }

    path = _camo_db_path()
    request = urllib.request.Request(
        CUSTOM_CAMOS_URL,
        headers={
            "User-Agent": "BO3Tracker custom-camos-sync",
            "Accept": "application/json",
        },
    )

    etag = str(app_config.get("custom_camos_etag", "") or "").strip()
    last_modified = str(app_config.get("custom_camos_last_modified", "") or "").strip()
    if etag:
        request.add_header("If-None-Match", etag)
    if last_modified:
        request.add_header("If-Modified-Since", last_modified)

    app_config["custom_camos_last_check"] = now

    try:
        response_handle, tls_fallback_used = _open_request_with_tls_fallback(request)
        with response_handle as response:
            raw = response.read()
            text = raw.decode("utf-8-sig")
            _validate_camo_payload(text)

            remote_hash = _sha256_text(text)
            local_hash = _load_local_hash(path)
            app_config["custom_camos_etag"] = response.headers.get("ETag", etag)
            app_config["custom_camos_last_modified"] = response.headers.get("Last-Modified", last_modified)
            app_config["custom_camos_hash"] = remote_hash
            app_config["custom_camos_tls_fallback_used"] = bool(tls_fallback_used)

            if remote_hash == local_hash:
                app_config["custom_camos_last_result"] = "unchanged"
                return {"ok": True, "changed": False, "msg": "Custom camos already up to date."}

            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(json.loads(text), handle, indent=4)
            os.replace(tmp_path, path)
            app_config["custom_camos_last_updated"] = now
            app_config["custom_camos_last_result"] = "updated"
            return {"ok": True, "changed": True, "msg": "Custom camos database updated."}
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            app_config["custom_camos_last_result"] = "not_modified"
            return {"ok": True, "changed": False, "msg": "Custom camos already up to date."}
        app_config["custom_camos_last_error"] = f"HTTP {exc.code}"
        return {"ok": False, "changed": False, "msg": f"Custom camos sync failed: HTTP {exc.code}."}
    except Exception as exc:
        app_config["custom_camos_last_error"] = str(exc)
        return {"ok": False, "changed": False, "msg": f"Custom camos sync failed: {exc}"}
