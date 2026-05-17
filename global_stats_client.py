import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from app_metadata import APP_VERSION
from file_utils import load_json, save_json

SUBMIT_URL = "https://uemmaps.com/tracker/submit_stats.php"
INGEST_TOKEN = "7c3d0a5cb97b4c4c8a17ed5a1d96e0fdbdf6a24fc1f44e7399684ffb7d399bf8"
MAX_BATCH_SIZE = 100
MIN_SYNC_INTERVAL_SECONDS = 15 * 60
MANUAL_SYNC_INTERVAL_SECONDS = 2 * 60


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(value, fallback="", limit=120):
    if value is None:
        return fallback
    text = str(value).replace("\x00", "").strip()
    return (text or fallback)[:limit]


def safe_int(value, default=0):
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return default


def get_game_and_players(match_data):
    game = match_data.get("game") or match_data.get("data", {}).get("game", {})
    players = match_data.get("players") or match_data.get("data", {}).get("players", {})
    return game if isinstance(game, dict) else {}, players if isinstance(players, dict) else {}


def get_or_create_state(state_path):
    state_file = Path(state_path)
    if state_file.exists():
        try:
            state = load_json(state_file)
            if isinstance(state, dict) and state.get("install_id"):
                state.setdefault("uploaded_match_hashes", [])
                state.setdefault("last_sync_at", 0)
                return state
        except (OSError, json.JSONDecodeError):
            pass

    state = {
        "install_id": str(uuid.uuid4()),
        "created_at": int(time.time()),
        "uploaded_match_hashes": [],
        "last_sync_at": 0,
    }

    save_json(state_file, state)
    return state


def contributor_hash(state):
    return sha256_text("bo3tracker-global-stats:" + str(state["install_id"]))


def get_local_player(players):
    player = players.get("0")
    if isinstance(player, dict):
        return player
    for player in players.values():
        if isinstance(player, dict):
            return player
    return {}


def summarize_weapons(players):
    weapons_by_name = {}

    for player in players.values():
        if not isinstance(player, dict):
            continue
        raw_weapons = player.get("weapon_data") or player.get("top5") or {}
        if not isinstance(raw_weapons, dict):
            continue

        for weapon in raw_weapons.values():
            if not isinstance(weapon, dict):
                continue
            name = clean_text(
                weapon.get("display")
                or weapon.get("display_name")
                or weapon.get("name"),
                limit=120,
            )
            if not name or name.lower() == "none":
                continue

            entry = weapons_by_name.setdefault(
                name,
                {"name": name, "kills": 0, "headshots": 0, "damage": 0},
            )
            entry["kills"] += safe_int(weapon.get("kills"))
            entry["headshots"] += safe_int(weapon.get("headshots"))
            entry["damage"] += safe_int(weapon.get("damage"))

    return sorted(
        weapons_by_name.values(),
        key=lambda item: (item["kills"], item["damage"]),
        reverse=True,
    )


def summarize_match_file(path, state):
    path = Path(path)
    try:
        match_data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(match_data, dict):
        return None

    game, players = get_game_and_players(match_data)
    if not game:
        return None

    raw_game_id = clean_text(game.get("game_id") or path.stem, fallback=path.stem, limit=160)
    map_name = clean_text(game.get("map_played"), fallback="Unknown", limit=120)
    round_reached = safe_int(game.get("rounds_total"))
    duration_seconds = safe_int(game.get("time_total"))

    if map_name == "Unknown" and round_reached == 0 and duration_seconds == 0:
        return None

    local_player = get_local_player(players)
    career_player_points = safe_int(local_player.get("player_points_gained"))
    career_gobblegums = safe_int(local_player.get("gobblegums_used"))

    total_kills = 0
    total_headshots = 0
    total_downs = 0
    total_revives = 0
    total_match_xp = 0

    for player in players.values():
        if not isinstance(player, dict):
            continue
        total_kills += safe_int(player.get("kills"))
        total_headshots += safe_int(player.get("headshots"))
        total_downs += safe_int(player.get("downs"))
        total_revives += safe_int(player.get("revives"))
        total_match_xp += safe_int(player.get("match_xp_earned"))

    game_id_hash = sha256_text("bo3tracker-game-id:" + raw_game_id)
    fingerprint = "|".join([game_id_hash, map_name, str(round_reached), str(duration_seconds)])

    return {
        "match_hash": sha256_text(fingerprint),
        "game_id_hash": game_id_hash,
        "source_version": clean_text(game.get("version"), limit=24),
        "map": map_name.replace("_", " ").title(),
        "mode": clean_text(game.get("gamemode"), limit=40),
        "round": round_reached,
        "duration_seconds": duration_seconds,
        "player_count": max(1, len(players)),
        "total_kills": total_kills,
        "total_headshots": total_headshots,
        "total_downs": total_downs,
        "total_revives": total_revives,
        "total_match_xp": total_match_xp,
        "career_player_points": career_player_points,
        "career_gobblegums": career_gobblegums,
        "zpm": round(safe_float(game.get("zpm")), 3),
        "weapons": summarize_weapons(players),
    }


def scan_history_folder(history_path, state, include_uploaded=False):
    folder = Path(history_path)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError("History folder not found: {}".format(folder))

    summaries = []
    uploaded = set(state.get("uploaded_match_hashes", []))

    for path in sorted(folder.glob("Game_*.json")):
        summary = summarize_match_file(path, state)
        if not summary:
            continue
        if not include_uploaded and summary["match_hash"] in uploaded:
            continue
        summaries.append(summary)

    return summaries


def build_career_profile(summaries):
    career_player_points = max((safe_int(item.get("career_player_points")) for item in summaries), default=0)
    career_gobblegums = max((safe_int(item.get("career_gobblegums")) for item in summaries), default=0)
    anchor = summaries[0].get("game_id_hash", "unknown") if summaries else "unknown"
    profile_hash = sha256_text(
        "bo3tracker-profile-anchor:{}".format(anchor)
    )
    return {
        "profile_hash": profile_hash,
        "career_player_points": career_player_points,
        "career_gobblegums": career_gobblegums,
    }


def chunked(items, size):
    return [items[index:index + size] for index in range(0, len(items), size)]


def upload_summaries(state, summaries, profile_summaries=None, timeout=20):
    totals = {"accepted": 0, "updated": 0, "duplicates": 0, "rejected": 0, "requests": 0}
    uploaded_hashes = set(state.get("uploaded_match_hashes", []))
    profile = build_career_profile(profile_summaries or summaries)
    batches = chunked(summaries, MAX_BATCH_SIZE) if summaries else [[]]

    for batch in batches:
        payload = {
            "app_version": APP_VERSION,
            "contributor_hash": contributor_hash(state),
            "profile": profile,
            "matches": batch,
        }
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            SUBMIT_URL,
            data=encoded,
            headers={
                "Content-Type": "application/json",
                "X-Global-Stats-Token": INGEST_TOKEN,
                "User-Agent": f"BO3TrackerGlobalStats/{APP_VERSION}",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        if not result.get("ok"):
            raise RuntimeError("Upload rejected: {}".format(result))

        totals["requests"] += 1
        totals["accepted"] += safe_int(result.get("accepted"))
        totals["updated"] += safe_int(result.get("updated"))
        totals["duplicates"] += safe_int(result.get("duplicates"))
        totals["rejected"] += safe_int(result.get("rejected"))

        for summary in batch:
            uploaded_hashes.add(summary["match_hash"])

    state["uploaded_match_hashes"] = sorted(uploaded_hashes)
    state["last_sync_at"] = int(time.time())
    return totals


def sync_history(history_path, state_path, force=False):
    state = get_or_create_state(state_path)
    now = int(time.time())
    interval = MANUAL_SYNC_INTERVAL_SECONDS if force else MIN_SYNC_INTERVAL_SECONDS
    if now - int(state.get("last_sync_at", 0)) < interval:
        return {"ok": True, "skipped": True, "reason": "rate_limited_locally"}

    all_summaries = scan_history_folder(history_path, state, include_uploaded=True)
    summaries = (
        all_summaries
        if force
        else [item for item in all_summaries if item["match_hash"] not in set(state.get("uploaded_match_hashes", []))]
    )
    if not all_summaries:
        state["last_sync_at"] = now
        save_json(state_path, state)
        return {"ok": True, "uploaded": 0, "skipped": True, "reason": "no_history"}

    try:
        result = upload_summaries(state, summaries, profile_summaries=all_summaries)
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        state["last_error"] = str(exc)
        state["last_error_at"] = now
        save_json(state_path, state)
        return {"ok": False, "error": str(exc)}

    state["last_result"] = result
    state.pop("last_error", None)
    save_json(state_path, state)
    result["ok"] = True
    result["uploaded"] = result.get("accepted", 0) + result.get("updated", 0) + result.get("duplicates", 0)
    return result
