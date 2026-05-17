"""Best-match summary and storage helpers for BO3 Tracker."""

import json
import os
import time

from app_paths import get_runtime_path


BEST_MATCHES_FILE = "best_matches.json"


def _load_json(path):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)
        return True
    except Exception:
        return False


def get_game_summary(data, fallback_id=None, fallback_date=None):
    game = data.get("game") or data.get("data", {}).get("game", {}) if data else {}
    players = data.get("players") or data.get("data", {}).get("players", {}) if data else {}
    game_id = str(game.get("game_id", fallback_id or "unknown"))
    map_name = str(game.get("map_played", "Unknown Map")).replace("_", " ").title()
    rounds = int(game.get("rounds_total", 0))
    time_sec = int(game.get("time_total", 0))
    mins, secs = divmod(time_sec, 60)
    hours, mins = divmod(mins, 60)
    time_str = f"{hours}h {mins}m" if hours else f"{mins}m {secs}s"
    p0 = players.get("0", next(iter(players.values()), {})) if players else {}
    match_xp = int(p0.get("match_xp_earned", 0)) if p0 else 0
    return {
        "id": game_id,
        "map": map_name,
        "round": rounds,
        "time": time_str,
        "match_xp": match_xp,
        "date": fallback_date or "",
    }


def get_best_matches_path():
    return get_runtime_path(BEST_MATCHES_FILE)


def load_best_matches():
    raw = _load_json(get_best_matches_path()) or []
    if isinstance(raw, dict):
        raw = raw.get("matches", [])
    matches = []
    seen = set()
    for item in raw:
        if isinstance(item, str):
            item = {"id": item}
        if not isinstance(item, dict) or not item.get("id"):
            continue
        item["id"] = str(item["id"])
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        matches.append(item)
    return matches


def save_best_matches(matches):
    return _save_json(get_best_matches_path(), matches)


def find_archive_data(hist_path, game_id, live_data=None):
    safe_id = sanitize_game_id(game_id)
    archive_path = os.path.join(hist_path, f"Game_{safe_id}.json")
    if os.path.exists(archive_path):
        return _load_json(archive_path), True
    return live_data, False


def sanitize_game_id(game_id):
    return (
        str(game_id or "")
        .strip()
        .replace(":", "_")
        .replace("|", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def add_best_match_from_data(game_id, archive_data):
    safe_id = sanitize_game_id(game_id)
    if not safe_id:
        return {"success": False, "msg": "No game ID was provided."}
    if not archive_data:
        return {"success": False, "msg": f"Could not find archived match for game ID {safe_id}."}

    summary = get_game_summary(archive_data, fallback_id=safe_id)
    summary["id"] = safe_id
    summary["date"] = time.strftime("%b %d, %Y %I:%M %p", time.localtime())
    summary["added_at"] = int(time.time())

    matches = load_best_matches()
    if any(sanitize_game_id(m.get("id")) == safe_id for m in matches):
        return {"success": False, "msg": "This match is already saved as a best match."}

    matches.insert(0, summary)
    if save_best_matches(matches):
        return {
            "success": True,
            "msg": f"Saved best match: {summary['map']} // Round {summary['round']}",
            "item": summary,
        }
    return {"success": False, "msg": "Could not save best_matches.json."}


def get_best_matches_with_archive_status(hist_path):
    matches = load_best_matches()
    results = []

    for item in matches:
        game_id = sanitize_game_id(item.get("id", ""))
        result = dict(item)
        result["exists"] = False

        if hist_path and game_id:
            archive_path = os.path.join(hist_path, f"Game_{game_id}.json")
            if os.path.exists(archive_path):
                archive_data = _load_json(archive_path)
                if archive_data:
                    fallback_date = result.get("date", "")
                    result = get_game_summary(archive_data, fallback_id=game_id, fallback_date=fallback_date)
                    result["exists"] = True

        result.setdefault("map", "Unknown Map")
        result.setdefault("round", 0)
        result.setdefault("time", "0m 0s")
        result.setdefault("match_xp", 0)
        result.setdefault("date", "")
        result["id"] = game_id
        results.append(result)

    return results


def remove_best_match_by_id(game_id):
    safe_id = sanitize_game_id(game_id)
    if not safe_id:
        return {"success": False, "msg": "No game ID was provided."}

    matches = load_best_matches()
    updated = [m for m in matches if sanitize_game_id(m.get("id", "")) != safe_id]
    if len(updated) == len(matches):
        return {"success": False, "msg": "That match is not in Best Matches."}

    if save_best_matches(updated):
        return {"success": True, "msg": "Removed best match."}
    return {"success": False, "msg": "Could not update best_matches.json."}
