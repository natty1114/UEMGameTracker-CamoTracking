"""Remote sync client for server-controlled map_challenges.json."""
import json
import ssl
import time
import urllib.error
import urllib.request


DEFAULT_CHECK_INTERVAL_SECONDS = 60 * 60


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
    """Fetch the authoritative map challenge list from the site."""
    now = int(time.time())
    last_check = int(app_config.get("map_challenges_sync_last_check", 0) or 0)
    if not force and last_check and now - last_check < interval_seconds:
        return {
            "ok": True,
            "skipped": True,
            "reason": "rate_limited_locally",
            "msg": "Map challenges sync skipped: recently checked.",
        }

    app_config["map_challenges_sync_last_check"] = now

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BO3Tracker map-challenges-sync",
            "Accept": "application/json",
        },
    )

    etag = str(app_config.get("map_challenges_remote_etag", "") or "").strip()
    if etag:
        request.add_header("If-None-Match", etag)

    try:
        response_handle, tls_fallback_used = _open_request_with_tls_fallback(request)
        with response_handle as response:
            raw = response.read()
            text = raw.decode("utf-8-sig")
            data = json.loads(text)
            if isinstance(data, dict):
                remote_challenges = data.get("challenges", data.get("data"))
                remote_version = str(data.get("version", "") or "")
                mode = str(data.get("mode", "replace") or "replace").strip().lower()
            else:
                remote_challenges = data
                remote_version = ""
                mode = "replace"

            if not isinstance(remote_challenges, list):
                return {"ok": False, "changed": False, "msg": "Remote response missing challenges list."}

            app_config["map_challenges_remote_etag"] = response.headers.get("ETag", etag)
            app_config["map_challenges_remote_tls_fallback_used"] = bool(tls_fallback_used)
            app_config["map_challenges_last_result"] = "fetched"
            if remote_version:
                app_config["map_challenges_remote_version"] = remote_version

            return {
                "ok": True,
                "changed": True,
                "challenges": remote_challenges,
                "version": remote_version,
                "mode": mode,
                "msg": "Map challenges fetched from remote.",
            }

    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            app_config["map_challenges_last_result"] = "not_modified"
            return {"ok": True, "changed": False, "challenges": None, "msg": "Map challenges already up to date."}
        app_config["map_challenges_last_error"] = f"HTTP {exc.code}"
        return {"ok": False, "changed": False, "msg": f"Map challenges sync failed: HTTP {exc.code}."}
    except Exception as exc:
        app_config["map_challenges_last_error"] = str(exc)
        return {"ok": False, "changed": False, "msg": f"Map challenges sync failed: {exc}"}
