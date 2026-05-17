"""Remote sync client for map_weapons.json."""
import json
import ssl
import time
import urllib.error
import urllib.request

from file_utils import load_json, save_json


DEFAULT_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


def _open_request_with_tls_fallback(request):
    try:
        return urllib.request.urlopen(request, timeout=10), False
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLError):
            context = ssl._create_unverified_context()
            return urllib.request.urlopen(request, timeout=10, context=context), True
        raise


def fetch(url, app_config, force=False, interval_seconds=DEFAULT_CHECK_INTERVAL_SECONDS):
    now = int(time.time())
    last_check = int(app_config.get("map_weapons_sync_last_check", 0) or 0)
    if not force and last_check and now - last_check < interval_seconds:
        return {
            "ok": True,
            "skipped": True,
            "reason": "rate_limited_locally",
            "msg": "Map weapons sync skipped: recently checked.",
        }

    app_config["map_weapons_sync_last_check"] = now

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BO3Tracker map-weapons-sync",
            "Accept": "application/json",
        },
    )

    etag = str(app_config.get("map_weapons_remote_etag", "") or "").strip()
    if etag:
        request.add_header("If-None-Match", etag)

    try:
        response_handle, tls_fallback_used = _open_request_with_tls_fallback(request)
        with response_handle as response:
            raw = response.read()
            text = raw.decode("utf-8-sig")
            data = json.loads(text)
            remote_data = data.get("data") if isinstance(data, dict) else None
            if not isinstance(remote_data, dict):
                return {"ok": False, "changed": False, "msg": "Remote response missing data object."}

            app_config["map_weapons_remote_etag"] = response.headers.get("ETag", etag)
            app_config["map_weapons_remote_tls_fallback_used"] = bool(tls_fallback_used)
            app_config["map_weapons_last_result"] = "fetched"

            return {"ok": True, "changed": True, "data": remote_data, "msg": "Map weapons fetched from remote."}

    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            app_config["map_weapons_last_result"] = "not_modified"
            return {"ok": True, "changed": False, "data": None, "msg": "Map weapons already up to date."}
        app_config["map_weapons_last_error"] = f"HTTP {exc.code}"
        return {"ok": False, "changed": False, "msg": f"Map weapons sync failed: HTTP {exc.code}."}
    except Exception as exc:
        app_config["map_weapons_last_error"] = str(exc)
        return {"ok": False, "changed": False, "msg": f"Map weapons sync failed: {exc}"}


def push(url, data, app_config):
    payload = json.dumps({"data": data}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "User-Agent": "BO3Tracker map-weapons-sync",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        response_handle, tls_fallback_used = _open_request_with_tls_fallback(request)
        with response_handle as response:
            raw = response.read()
            text = raw.decode("utf-8-sig")
            result = json.loads(text)
            app_config["map_weapons_push_last_result"] = "ok"
            return {"ok": True, "msg": "Map weapons pushed to remote.", "response": result}
    except Exception as exc:
        app_config["map_weapons_push_last_error"] = str(exc)
        return {"ok": False, "msg": f"Map weapons push failed: {exc}"}
