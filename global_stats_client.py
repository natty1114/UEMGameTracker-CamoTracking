import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from app_metadata import APP_VERSION
from file_utils import load_json, save_json
from game_data import IGNORE_KEYWORDS, PERK_NAMES

SUBMIT_URL = "https://uemmaps.com/tracker/submit_stats.php"
INGEST_TOKEN = "7c3d0a5cb97b4c4c8a17ed5a1d96e0fdbdf6a24fc1f44e7399684ffb7d399bf8"
MAX_BATCH_SIZE = 100
MAX_BATCH_PAYLOAD_BYTES = 100000
MIN_SYNC_INTERVAL_SECONDS = 15 * 60
MANUAL_SYNC_INTERVAL_SECONDS = 2 * 60
LEADERBOARD_BACKFILL_VERSION = "4.7.0"
MIN_GLOBAL_STATS_ROUND = 4


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(value, fallback="", limit=120):
    if value is None:
        return fallback
    text = str(value).replace("\x00", "").strip()
    return (text or fallback)[:limit]


def clean_optional_text(value, limit=120):
    text = clean_text(value, limit=limit)
    if text.lower() in ("none", "null", "0"):
        return ""
    return text


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


def client_reference(state):
    return "BT-" + contributor_hash(state)[:10].upper()


def get_local_player(players):
    player = players.get("0")
    if isinstance(player, dict):
        return player
    for player in players.values():
        if isinstance(player, dict):
            return player
    return {}


def format_aat_name(value):
    text = clean_optional_text(value, limit=80)
    if not text:
        return ""
    lowered = text.lower()
    for prefix in ("zm_aat_", "aat_", "specialty_"):
        if lowered.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.replace("_", " ").replace("-", " ").title()


def format_perk_name(value):
    text = clean_optional_text(value, limit=80)
    if not text:
        return ""
    return PERK_NAMES.get(text, text.replace("specialty_", "").replace("_", " ").replace("-", " ").title())


def summarize_players(players):
    summaries = []

    def player_sort_key(item):
        pid = str(item[0])
        try:
            return (0, int(pid))
        except ValueError:
            return (1, pid)

    for index, (player_id, player) in enumerate(sorted(players.items(), key=player_sort_key), start=1):
        if not isinstance(player, dict):
            continue

        perks = []
        raw_perks = player.get("perks") or []
        if isinstance(raw_perks, dict):
            raw_perks = list(raw_perks.values())
        if not isinstance(raw_perks, list):
            raw_perks = []

        seen_perks = set()
        for perk in raw_perks:
            perk_key = clean_optional_text(perk, limit=80)
            if not perk_key or any(keyword in perk_key.lower() for keyword in IGNORE_KEYWORDS):
                continue
            if perk_key in seen_perks:
                continue
            seen_perks.add(perk_key)
            perks.append({
                "key": perk_key,
                "name": format_perk_name(perk_key),
            })

        summaries.append({
            "slot": index,
            "label": "Player {}".format(index),
            "kills": safe_int(player.get("kills")),
            "headshots": safe_int(player.get("headshots")),
            "downs": safe_int(player.get("downs")),
            "revives": safe_int(player.get("revives")),
            "points": safe_int(player.get("points")),
            "match_xp": safe_int(player.get("match_xp_earned")),
            "perks": perks,
        })

    return summaries


def get_player_display_name(player):
    if not isinstance(player, dict):
        return ""
    return clean_optional_text(
        player.get("name")
        or player.get("playername")
        or player.get("player_name")
        or player.get("username")
        or player.get("display_name"),
        limit=80,
    )


def summarize_leaderboard_players(players, game, match_summary):
    summaries = []

    def player_sort_key(item):
        pid = str(item[0])
        try:
            return (0, int(pid))
        except ValueError:
            return (1, pid)

    for index, (player_id, player) in enumerate(sorted(players.items(), key=player_sort_key), start=1):
        if not isinstance(player, dict):
            continue
        display_name = get_player_display_name(player)
        if not display_name:
            continue

        summaries.append({
            "slot": index,
            "name": display_name,
            "level": safe_int(player.get("level"), 1),
            "prestige": safe_int(player.get("prestige")),
            "prestige_legend": safe_int(player.get("prestige_legend")),
            "prestige_absolute": safe_int(player.get("prestige_absolute")),
            "prestige_ultimate": safe_int(player.get("prestige_ultimate")),
            "kills": safe_int(player.get("kills")),
            "headshots": safe_int(player.get("headshots")),
            "downs": safe_int(player.get("downs")),
            "revives": safe_int(player.get("revives")),
            "match_xp": safe_int(player.get("match_xp_earned")),
            "round": safe_int(match_summary.get("round")),
            "map": clean_text(match_summary.get("map"), limit=120),
            "duration_seconds": safe_int(match_summary.get("duration_seconds")),
            "zpm": round(safe_float(game.get("zpm")), 3),
        })

    return summaries


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
                {
                    "name": name,
                    "kills": 0,
                    "headshots": 0,
                    "damage": 0,
                    "packed_name": "",
                    "enchant_level": 0,
                    "repack_level": 0,
                    "aat_key": "",
                    "aat_name": "",
                },
            )
            entry["kills"] += safe_int(weapon.get("kills"))
            entry["headshots"] += safe_int(weapon.get("headshots"))
            entry["damage"] += safe_int(weapon.get("damage"))
            entry["enchant_level"] = max(entry["enchant_level"], safe_int(weapon.get("enchant")))
            entry["repack_level"] = max(entry["repack_level"], safe_int(weapon.get("repack_level")))

            packed_name = clean_optional_text(weapon.get("display_name_upgraded"), limit=120)
            if packed_name and not entry["packed_name"]:
                entry["packed_name"] = packed_name

            aat_key = clean_optional_text(
                weapon.get("currentAAT") or weapon.get("current_aat") or weapon.get("aat"),
                limit=80,
            )
            if aat_key and not entry["aat_key"]:
                entry["aat_key"] = aat_key
                entry["aat_name"] = format_aat_name(aat_key)

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

    history_game_id = clean_text(path.stem, fallback="", limit=160)
    raw_game_id = clean_text(game.get("game_id") or history_game_id, fallback=history_game_id, limit=160)
    map_name = clean_text(game.get("map_played"), fallback="Unknown", limit=120)
    round_reached = safe_int(game.get("rounds_total"))
    duration_seconds = safe_int(game.get("time_total"))

    if map_name == "Unknown" and round_reached == 0 and duration_seconds == 0:
        return None
    if round_reached < MIN_GLOBAL_STATS_ROUND:
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

    summary = {
        "match_hash": sha256_text(fingerprint),
        "client_version": APP_VERSION,
        "game_id": raw_game_id,
        "history_game_id": history_game_id,
        "game_id_hash": game_id_hash,
        "source_version": clean_text(game.get("version"), limit=24),
        "map": map_name.replace("_", " ").title(),
        "workshop_id": clean_text(
            game.get("steam_link")
            or game.get("workshop_link")
            or game.get("workshop_url")
            or game.get("workshop_id"),
            limit=32,
        ),
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
        "players": summarize_players(players),
        "weapons": summarize_weapons(players),
    }
    summary["leaderboard_players"] = summarize_leaderboard_players(players, game, summary)
    return summary


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


def build_upload_payload(state, profile, batch):
    return {
        "app_version": APP_VERSION,
        "client_version": APP_VERSION,
        "contributor_hash": contributor_hash(state),
        "client_ref": client_reference(state),
        "profile": profile,
        "matches": batch,
    }


def payload_size_bytes(state, profile, batch):
    payload = build_upload_payload(state, profile, batch)
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def chunked_upload_batches(state, profile, summaries):
    if not summaries:
        return [[]]

    batches = []
    current = []
    for summary in summaries:
        candidate = current + [summary]
        if (
            current
            and len(candidate) > 1
            and (
                len(candidate) > MAX_BATCH_SIZE
                or payload_size_bytes(state, profile, candidate) > MAX_BATCH_PAYLOAD_BYTES
            )
        ):
            batches.append(current)
            current = [summary]
        else:
            current = candidate

    if current:
        batches.append(current)
    return batches


def upload_summaries(state, summaries, profile_summaries=None, timeout=20):
    totals = {"accepted": 0, "updated": 0, "duplicates": 0, "rejected": 0, "requests": 0}
    uploaded_hashes = set(state.get("uploaded_match_hashes", []))
    profile = build_career_profile(profile_summaries or summaries)
    batches = chunked_upload_batches(state, profile, summaries)

    for batch in batches:
        payload = build_upload_payload(state, profile, batch)
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
    if not all_summaries:
        state["last_sync_at"] = now
        save_json(state_path, state)
        return {"ok": True, "uploaded": 0, "skipped": True, "reason": "no_history"}

    uploaded_hashes = set(state.get("uploaded_match_hashes", []))
    pending_summaries = [item for item in all_summaries if item["match_hash"] not in uploaded_hashes]
    needs_leaderboard_backfill = state.get("leaderboard_backfill_version") != LEADERBOARD_BACKFILL_VERSION
    leaderboard_backfill_summaries = (
        [item for item in all_summaries if item.get("leaderboard_players")]
        if needs_leaderboard_backfill
        else []
    )

    if force:
        summaries = all_summaries
    elif leaderboard_backfill_summaries:
        summaries_by_hash = {item["match_hash"]: item for item in pending_summaries}
        for item in leaderboard_backfill_summaries:
            summaries_by_hash[item["match_hash"]] = item
        summaries = list(summaries_by_hash.values())
    else:
        summaries = pending_summaries

    try:
        result = upload_summaries(state, summaries, profile_summaries=all_summaries)
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        state["last_error"] = str(exc)
        state["last_error_at"] = now
        save_json(state_path, state)
        return {"ok": False, "error": str(exc)}

    if needs_leaderboard_backfill:
        state["leaderboard_backfill_version"] = LEADERBOARD_BACKFILL_VERSION
        result["leaderboard_backfilled"] = bool(leaderboard_backfill_summaries)
        result["leaderboard_backfill_matches"] = len(leaderboard_backfill_summaries)
    state["last_result"] = result
    state.pop("last_error", None)
    save_json(state_path, state)
    result["ok"] = True
    result["uploaded"] = result.get("accepted", 0) + result.get("updated", 0) + result.get("duplicates", 0)
    return result
