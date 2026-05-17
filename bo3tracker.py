import os
import json
import glob
import time
import threading
import webview # pip install pywebview
import sys
import subprocess
import urllib.request
import zipfile

# --- CUSTOM IMPORTS ---
from asset_helpers import (
    get_base64_icon,
    get_calling_card_src,
    get_emblem_src,
    get_level_icon_src,
    get_prestige_icon_src,
    get_tier_icon_src,
    inline_theme_asset_urls,
    load_css,
    sanitize_filename,
)
from app_metadata import APP_VERSION, GLOBAL_STATS_PROMPT_VERSION, REMOTE_MANAGEMENT_URL, MAP_WEAPONS_SYNC_URL, MAP_CHALLENGES_SYNC_URL
from app_paths import get_base_path, get_config_dir, get_runtime_path, migrate_all_runtime_paths
from best_matches import (
    add_best_match_from_data,
    find_archive_data,
    get_best_matches_with_archive_status,
    remove_best_match_by_id,
    sanitize_game_id,
)
from camo_processor import process_camo_data as build_camo_data
from challenge_system import ChallengeManager
from custom_camos_sync import sync_custom_camos
from discord_presence import discord_presence
from map_weapons import map_weapons_manager
from match_xp import xp_tracker_instance
from xpm_grapher import xpm_grapher_instance
from workshop_images import get_workshop_image, get_workshop_image_url
from weapon_categories import WEAPON_CATEGORY_LABELS, get_weapon_category, normalise_weapon_category
import global_stats_client
from remote_management_client import fetch_remote_management
from ui_main import build_main_app_html
from ui_views import build_setup_html, build_unified_overlay_html, build_graph_overlay_html, build_xp_debugger_html
from game_data import (
    ALWAYS_AVAILABLE_THEMES,
    CONFIG_FILE,
    CSS_MAIN_FILE,
    CSS_SETUP_FILE,
    DEFAULT_DISCORD_APPLICATION_ID,
    DISCORD_ACTIVITY_NAME,
    GITHUB_RELEASES_API,
    GLOBAL_STATS_STATE_FILE,
    LANGUAGE_OPTIONS,
    REMOTE_MANAGEMENT_CACHE_FILE,
    THEMES_DIR,
    TRACKER_GITHUB_URL,
    UEM_WORKSHOP_URL,
    UPDATER_EXE_NAME,
)
from overlay_themes import (
    OVERLAY_BASE_HEIGHT,
    OVERLAY_BASE_WIDTH,
    OVERLAY_SIZE_DEFAULT,
    OVERLAY_SIZE_MAX,
    OVERLAY_SIZE_MIN,
    OVERLAY_THEMES,
)
from file_utils import load_json, save_json
from player_stats_backup import (
    create_player_stats_backup,
    find_player_stats_files,
    normalize_backup_path,
    restore_player_stats_backup,
)
from version_utils import parse_version_parts, is_version_newer, get_updater_launch_path
from stats_processor import process_stats, damage_tracker

# --- GLOBAL STATE ---
app_config = {}
window = None
# -- OVERLAY GLOBALS --
unified_window = None
stop_overlays = False
xp_debug_window = None
xp_debug_rows = []
xp_debug_lock = threading.Lock()
graph_overlay_window = None
stop_graph_overlay = False
global_stats_sync_lock = threading.Lock()
global_stats_sync_running = False
custom_camos_sync_lock = threading.Lock()
custom_camos_sync_running = False
map_weapons_sync_lock = threading.Lock()
map_weapons_sync_running = False
map_weapons_push_lock = threading.Lock()
map_weapons_push_running = False
map_challenges_sync_lock = threading.Lock()
map_challenges_sync_running = False
remote_management = {}
last_discord_presence_update = 0
discord_presence_update_lock = threading.Lock()
discord_presence_update_running = False
discord_presence_workshop_image_cache = {}
# ---------------------

def get_overlay_size_percent():
    try:
        value = int(float(app_config.get("overlay_size_percent", OVERLAY_SIZE_DEFAULT)))
    except (TypeError, ValueError):
        value = OVERLAY_SIZE_DEFAULT
    return max(OVERLAY_SIZE_MIN, min(OVERLAY_SIZE_MAX, value))

def get_overlay_scale():
    return get_overlay_size_percent() / 100.0

def get_scaled_overlay_dimension(value):
    return max(1, int(round(value * get_overlay_scale())))

def get_global_stats_state_path():
    return get_runtime_path(GLOBAL_STATS_STATE_FILE)

def get_remote_management_cache_path():
    return get_runtime_path(REMOTE_MANAGEMENT_CACHE_FILE)

def refresh_remote_management():
    global remote_management, app_config
    result = fetch_remote_management(REMOTE_MANAGEMENT_URL, get_remote_management_cache_path())
    remote_management = result.get("management") or {}
    app_config["remote_management_last_source"] = result.get("source", "")
    app_config["remote_management_last_ok"] = bool(result.get("ok", False))
    app_config["remote_management_last_error"] = result.get("error", "")
    app_config["remote_management_last_version"] = str(remote_management.get("version", ""))
    save_app_config()
    return result

def apply_remote_management():
    challenges = remote_management.get("challenges") if isinstance(remote_management, dict) else {}
    if isinstance(challenges, dict) and challenges.get("enabled", False):
        applied = challenge_manager.apply_remote_manifest(
            challenges.get("manifest", {}),
            replace=challenges.get("replace", True),
        )
        app_config["remote_challenges_applied"] = bool(applied)
        app_config["remote_challenges_version"] = str(challenges.get("manifest", {}).get("version", ""))
        save_app_config()
        return applied
    return False

def get_global_stats_management_control_path():
    return os.path.join(get_base_path(), "dev_tools", "management_outputs", "global_stats_control.json")

def get_global_stats_management_control():
    path = get_global_stats_management_control_path()
    if not os.path.exists(path):
        return {"global_stats_enabled": True, "message": ""}
    try:
        data = load_json(path)
    except Exception:
        return {"global_stats_enabled": True, "message": ""}
    if not isinstance(data, dict):
        return {"global_stats_enabled": True, "message": ""}
    return {
        "global_stats_enabled": bool(data.get("global_stats_enabled", True)),
        "message": str(data.get("message", "") or ""),
    }

def save_app_config():
    return save_json(get_runtime_path(CONFIG_FILE), app_config)

def is_discord_presence_enabled():
    return bool(app_config.get("discord_presence_enabled", False))

def get_discord_presence_client_id():
    return str(app_config.get("discord_presence_client_id", "") or DEFAULT_DISCORD_APPLICATION_ID).strip()

def configure_discord_presence():
    discord_presence.configure(get_discord_presence_client_id())

def _format_presence_map_name(value):
    text = str(value or "Unknown Map").replace("_", " ").strip()
    return text.title() if text else "Unknown Map"

def _safe_int(value, default=0):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return default

def _extract_steam_workshop_id(value):
    text = str(value or "").strip()
    if not text or text == "0":
        return ""
    if "id=" in text:
        return text.split("id=", 1)[1].split("&", 1)[0].strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits or text

def _get_presence_workshop_image(game):
    configured = str(app_config.get("discord_presence_large_image", "") or "").strip()
    steam_link = (
        game.get("steam_link")
        or game.get("workshop_link")
        or game.get("workshop_url")
        or game.get("workshop_id")
        or ""
    )
    workshop_id = _extract_steam_workshop_id(steam_link)
    if not workshop_id:
        return configured
    if workshop_id in discord_presence_workshop_image_cache:
        return discord_presence_workshop_image_cache[workshop_id] or configured
    image_url = get_workshop_image_url(workshop_id)
    discord_presence_workshop_image_cache[workshop_id] = image_url or ""
    return image_url or configured

def _format_presence_rank(player):
    ultimate = _safe_int(player.get("prestige_ultimate"))
    absolute = _safe_int(player.get("prestige_absolute"))
    legend = _safe_int(player.get("prestige_legend"))
    prestige = _safe_int(player.get("prestige"))
    level = _safe_int(player.get("level"), 1)
    parts = []
    if ultimate:
        parts.append(f"U{ultimate}")
    if absolute:
        parts.append(f"A{absolute}")
    if legend:
        parts.append(f"Legend {legend}")
    if prestige:
        parts.append(f"P{prestige}")
    parts.append(f"Lv {level}")
    return " ".join(parts)

def _get_presence_match_xp(game_id, player_id, player):
    if "match_xp_earned" in player:
        return _safe_int(player.get("match_xp_earned"))
    return xp_tracker_instance.calculate_match_xp(
        game_id,
        player_id,
        _safe_int(player.get("prestige")),
        _safe_int(player.get("level"), 1),
        _safe_int(player.get("xp", player.get("total_xp", 0))),
        _safe_int(player.get("prestige_legend")),
        app_config.get("xp_overflow_recovery_enabled", False),
        _safe_int(player.get("prestige_absolute")),
        _safe_int(player.get("prestige_ultimate")),
    )

def _format_presence_level_xp_bar(player):
    level = _safe_int(player.get("level"), 1)
    legend = _safe_int(player.get("prestige_legend"))
    current_xp = _safe_int(player.get("xp", player.get("total_xp", 0)))
    required_xp = xp_tracker_instance.get_xp_required(level, legend)
    if required_xp <= 0:
        return ""
    pct = max(0, min(100, int(round((current_xp / required_xp) * 100))))
    filled = max(0, min(10, int(round(pct / 10))))
    return "[{}{}] {}%".format("#" * filled, "-" * (10 - filled), pct)

def _format_presence_weapon(player):
    weapons = player.get("top5", player.get("weapon_data", {}))
    if not isinstance(weapons, dict):
        return ""
    best_weapon = None
    best_damage = -1
    for console_name, weapon in weapons.items():
        if not isinstance(weapon, dict):
            continue
        display = str(weapon.get("display") or weapon.get("display_name") or console_name or "Unknown")
        if not display or display.lower() == "none":
            continue
        damage = _safe_int(weapon.get("damage"))
        if damage > best_damage:
            best_damage = damage
            best_weapon = weapon
    if not best_weapon:
        return ""
    name = str(best_weapon.get("display") or best_weapon.get("display_name") or "Unknown")
    kills = _safe_int(best_weapon.get("kills"))
    return f"{name[:26]} ({kills:,}k)"

def update_discord_presence_from_game(current_data, force=False):
    global last_discord_presence_update
    if not is_discord_presence_enabled():
        return False

    now = int(time.time())
    if not force and now - last_discord_presence_update < 15:
        return True

    configure_discord_presence()
    if not get_discord_presence_client_id():
        app_config["discord_presence_last_status"] = "Discord client ID is not configured."
        save_app_config()
        return False

    game = current_data.get("game") or current_data.get("data", {}).get("game", {})
    game_id = str(game.get("game_id", "unknown"))
    players = current_data.get("players") or current_data.get("data", {}).get("players", {})
    primary_player_id = "0"
    primary_player = players.get("0") if isinstance(players, dict) else None
    if not primary_player and isinstance(players, dict) and players:
        primary_player_id, primary_player = next(iter(players.items()))

    map_name = _format_presence_map_name(game.get("map_played", "Unknown Map"))
    try:
        round_num = int(game.get("rounds_total", 0) or 0)
    except (TypeError, ValueError):
        round_num = 0

    details = f"Round {round_num} on {map_name}" if round_num else f"Tracking {map_name}"
    if primary_player:
        kills = _safe_int(primary_player.get("kills"))
        match_xp = _get_presence_match_xp(game_id, primary_player_id, primary_player)
        rank = _format_presence_rank(primary_player)
        xp_bar = _format_presence_level_xp_bar(primary_player)
        weapon = _format_presence_weapon(primary_player)
        state_parts = [rank, f"+{match_xp:,} XP", f"{kills:,} kills"]
        if weapon:
            state_parts.append(weapon)
        if xp_bar:
            state_parts.append(xp_bar)
        state = " | ".join(state_parts)
    else:
        state = "Watching live BO3 Zombies stats"

    large_image = _get_presence_workshop_image(game)
    ok = discord_presence.update(
        details=details,
        state=state,
        large_image=large_image,
        large_text="BO3 Tracker",
        name=DISCORD_ACTIVITY_NAME,
        buttons=[
            {"label": "Ultimate Experience Mod", "url": UEM_WORKSHOP_URL},
            {"label": "Community Tool", "url": TRACKER_GITHUB_URL},
        ],
    )
    last_discord_presence_update = now
    if ok:
        response_summary = discord_presence.get_last_response_summary()
        suffix = f" ({response_summary})" if response_summary else ""
        app_config["discord_presence_last_status"] = f"Activity sent: {details} | {state}{suffix}"
    else:
        app_config["discord_presence_last_status"] = discord_presence.last_error
    save_app_config()
    return ok

def schedule_discord_presence_update(current_data, force=False):
    global discord_presence_update_running
    if not is_discord_presence_enabled():
        return False
    with discord_presence_update_lock:
        if discord_presence_update_running:
            return False
        discord_presence_update_running = True

    def worker():
        global discord_presence_update_running
        try:
            update_discord_presence_from_game(current_data, force=force)
        finally:
            with discord_presence_update_lock:
                discord_presence_update_running = False

    t = threading.Thread(target=worker, name="discord-presence-update")
    t.daemon = True
    t.start()
    return True

def clear_discord_presence():
    try:
        discord_presence.clear()
        discord_presence.close()
    except Exception:
        pass

def get_t7_config_path():
    live_path = str(app_config.get("live_path", "") or "")
    if not live_path:
        return ""
    parts = os.path.normpath(live_path).split(os.sep)
    lowered = [part.lower() for part in parts]
    if "players" not in lowered:
        return ""
    players_index = lowered.index("players")
    players_dir = os.sep.join(parts[:players_index + 1])
    return os.path.join(players_dir, "t7.json")

def load_t7_config():
    path = get_t7_config_path()
    if not path or not os.path.exists(path):
        return path, None
    try:
        data = load_json(path)
    except Exception:
        return path, None
    return path, data if isinstance(data, dict) else None

def is_global_stats_enabled():
    remote_global_stats = remote_management.get("global_stats") if isinstance(remote_management, dict) else {}
    if isinstance(remote_global_stats, dict) and not remote_global_stats.get("enabled", True):
        return False
    if not get_global_stats_management_control().get("global_stats_enabled", True):
        return False
    return bool(app_config.get('global_stats_enabled', False))

def get_global_stats_management_message():
    remote_global_stats = remote_management.get("global_stats") if isinstance(remote_management, dict) else {}
    if isinstance(remote_global_stats, dict) and not remote_global_stats.get("enabled", True):
        return remote_global_stats.get("message") or "Anonymous global stats are currently disabled remotely."
    control = get_global_stats_management_control()
    if control.get("global_stats_enabled", True):
        return ""
    return control.get("message") or "Anonymous global stats are currently disabled by management tools."

def format_global_stats_result(result):
    if not isinstance(result, dict):
        return "Sync completed."
    if result.get("skipped"):
        reason = result.get("reason", "skipped")
        if reason == "rate_limited_locally":
            return "Sync skipped: please wait before syncing again."
        if reason == "nothing_new":
            return "Sync complete: no new matches to upload."
        if reason ==  "no_history":
            return "Sync skipped: no archived matches found."
        return f"Sync skipped: {reason}."
    if not result.get("ok", False):
        return "Sync failed."
    accepted = int(result.get("accepted", 0))
    updated = int(result.get("updated", 0))
    duplicates = int(result.get("duplicates", 0))
    return f"Sync complete: {accepted} new, {updated} updated, {duplicates} unchanged."

def schedule_global_stats_sync(reason="background", force=False):
    global global_stats_sync_running
    if not is_global_stats_enabled():
        return False

    hist_path = app_config.get('history_path')
    if not hist_path or not os.path.exists(hist_path):
        return False

    with global_stats_sync_lock:
        if global_stats_sync_running:
            return False
        global_stats_sync_running = True

    def worker():
        global global_stats_sync_running
        try:
            result = global_stats_client.sync_history(
                hist_path,
                get_global_stats_state_path(),
                force=force
            )
            app_config['global_stats_last_sync'] = int(time.time())
            app_config['global_stats_last_result'] = result
            app_config['global_stats_last_message'] = format_global_stats_result(result)
            save_app_config()
        except Exception as exc:
            app_config['global_stats_last_error'] = str(exc)
            app_config['global_stats_last_error_at'] = int(time.time())
            app_config['global_stats_last_message'] = f"Sync failed: {exc}"
            save_app_config()
        finally:
            with global_stats_sync_lock:
                global_stats_sync_running = False

    t = threading.Thread(target=worker, name=f"global-stats-{reason}")
    t.daemon = True
    t.start()
    return True

def schedule_custom_camos_sync(reason="background", force=False):
    global custom_camos_sync_running
    with custom_camos_sync_lock:
        if custom_camos_sync_running:
            return False
        custom_camos_sync_running = True

    def worker():
        global custom_camos_sync_running
        try:
            result = sync_custom_camos(app_config, force=force)
            app_config["custom_camos_last_message"] = result.get("msg", "Custom camos sync complete.")
            app_config["custom_camos_last_sync_reason"] = reason
            save_app_config()
        except Exception as exc:
            app_config["custom_camos_last_error"] = str(exc)
            app_config["custom_camos_last_message"] = f"Custom camos sync failed: {exc}"
            save_app_config()
        finally:
            with custom_camos_sync_lock:
                custom_camos_sync_running = False

    t = threading.Thread(target=worker, name=f"custom-camos-{reason}")
    t.daemon = True
    t.start()
    return True

def schedule_map_weapons_startup_sync():
    """Pull remote data, then push local discoveries (two-way startup sync)."""
    global map_weapons_sync_running
    with map_weapons_sync_lock:
        if map_weapons_sync_running:
            return False
        map_weapons_sync_running = True

    def worker():
        global map_weapons_sync_running
        try:
            pull = map_weapons_manager.sync_from_remote(MAP_WEAPONS_SYNC_URL, app_config, force=False)
            app_config["map_weapons_last_sync_msg"] = pull.get("msg", "")
            push = map_weapons_manager.push_to_remote(MAP_WEAPONS_SYNC_URL, app_config)
            if push.get("ok"):
                app_config["map_weapons_last_push_time"] = int(time.time())
            app_config["map_weapons_last_push_msg"] = push.get("msg", "")
            save_app_config()
        except Exception as exc:
            app_config["map_weapons_last_error"] = str(exc)
            save_app_config()
        finally:
            with map_weapons_sync_lock:
                map_weapons_sync_running = False

    t = threading.Thread(target=worker, name="map-weapons-startup")
    t.daemon = True
    t.start()
    return True

def schedule_map_weapons_push(reason="background"):
    """Push local discoveries to remote with 5-minute rate limit."""
    global map_weapons_push_running
    now = int(time.time())
    last_push = int(app_config.get("map_weapons_last_push_time", 0) or 0)
    if last_push and now - last_push < 300:
        return False
    with map_weapons_push_lock:
        if map_weapons_push_running:
            return False
        map_weapons_push_running = True

    def worker():
        global map_weapons_push_running
        try:
            result = map_weapons_manager.push_to_remote(MAP_WEAPONS_SYNC_URL, app_config)
            if result.get("ok"):
                app_config["map_weapons_last_push_time"] = int(time.time())
            app_config["map_weapons_push_last_msg"] = result.get("msg", "Map weapons push complete.")
            save_app_config()
        except Exception as exc:
            app_config["map_weapons_push_last_error"] = str(exc)
            app_config["map_weapons_push_last_msg"] = f"Map weapons push failed: {exc}"
            save_app_config()
        finally:
            with map_weapons_push_lock:
                map_weapons_push_running = False

    t = threading.Thread(target=worker, name=f"map-weapons-push-{reason}")
    t.daemon = True
    t.start()
    return True

def schedule_map_challenges_sync(reason="background", force=False):
    """Pull server-controlled map challenge definitions."""
    global map_challenges_sync_running
    with map_challenges_sync_lock:
        if map_challenges_sync_running:
            return False
        map_challenges_sync_running = True

    def worker():
        global map_challenges_sync_running
        try:
            result = challenge_manager.sync_map_challenges_from_remote(MAP_CHALLENGES_SYNC_URL, app_config, force=force)
            app_config["map_challenges_last_sync_msg"] = result.get("msg", "")
            app_config["map_challenges_last_sync_reason"] = reason
            save_app_config()
        except Exception as exc:
            app_config["map_challenges_last_error"] = str(exc)
            app_config["map_challenges_last_sync_msg"] = f"Map challenges sync failed: {exc}"
            save_app_config()
        finally:
            with map_challenges_sync_lock:
                map_challenges_sync_running = False

    t = threading.Thread(target=worker, name=f"map-challenges-{reason}")
    t.daemon = True
    t.start()
    return True

def get_overlay_theme(theme_name=None):
    theme_key = theme_name or app_config.get('active_theme', 'default')
    return OVERLAY_THEMES.get(theme_key, OVERLAY_THEMES["default"])

# Initialize Systems
challenge_manager = ChallengeManager(get_base_path()) 

# --- PROCESSOR (CAMO STATS) ---
def process_camo_data(user_json_path):
    return build_camo_data(user_json_path, app_config.get('starred', []))

# --- UNIFIED OVERLAY SYSTEM ---
def get_unified_overlay_html():
    return build_unified_overlay_html(json.dumps(get_overlay_theme()), json.dumps(get_overlay_scale()))

def overlay_loop():
    global unified_window, stop_overlays
    
    while not stop_overlays:
        if unified_window:
            path = app_config.get('live_path')
            if path and os.path.exists(path):
                try:
                    data = load_json(path)
                    stats = process_stats(
                        data,
                        is_live=True,
                        overflow_recovery_enabled=app_config.get('xp_overflow_recovery_enabled', False)
                    )
                    
                    if stats and stats['players']:
                        # Lock Overlay to Player 1 to save screen real estate
                        p_stats = stats['players'][0]
                        pid = p_stats['pid']
                        
                        game = data.get('game') or data.get('data', {}).get('game', {})
                        game_id = str(game.get('game_id', 'unknown'))
                        players = data.get('players') or data.get('data', {}).get('players', {})
                        top_3_weapons = []
                        
                        if players and pid in players:
                            p = players[pid]
                            weapons = p.get('top5', p.get('weapon_data', {}))
                            processed = []
                            for k, w in weapons.items():
                                if w.get('display') == 'none': continue
                                dname = str(w.get('display', 'Unknown'))
                                try: raw_dmg = int(float(w.get('damage', 0)))
                                except: raw_dmg = 0
                                
                                real_dmg = damage_tracker.get_real_damage(game_id, pid, k, raw_dmg)
                                
                                processed.append({
                                    "name": dname,
                                    "kills": str(w.get('kills', 0)),
                                    "damage": real_dmg,
                                    "damage_str": "{:,}".format(real_dmg)
                                })
                            processed.sort(key=lambda x: x['damage'], reverse=True)
                            top_3_weapons = processed[:3]

                        json_dmg = json.dumps(top_3_weapons)
                        json_perks = json.dumps(p_stats["perks"])
                        json_xp = json.dumps({
                            "match_xp": p_stats.get("match_xp", "0"),
                            "xpm": p_stats.get("xpm", "0"),
                            "rank_label": p_stats.get("overlay_rank", p_stats.get("rank_label", "")),
                            "rank_tier": p_stats.get("overlay_tier", ""),
                            "level": p_stats.get("level", ""),
                            "level_ups": p_stats.get("level_ups", 0),
                            "level_xp": p_stats.get("level_xp", 0),
                            "level_xp_required": p_stats.get("level_xp_required", 0),
                            "level_progress_pct": p_stats.get("level_progress_pct", 0)
                        })
                        json_theme = json.dumps(get_overlay_theme())
                        overlay_components = app_config.get('overlay_components', {})
                        component_settings = {
                            "perks": overlay_components.get("perks", True),
                            "damage": overlay_components.get("damage", True),
                            "rank": overlay_components.get("rank", True),
                            "xp": overlay_components.get("xp", True),
                            "progress": overlay_components.get("progress", True)
                        }
                        json_components = json.dumps(component_settings)
                        json_scale = json.dumps(get_overlay_scale())
                        unified_window.evaluate_js(f'applyOverlayTheme({json_theme}); setOverlayScale({json_scale}); updateOverlay({json_perks}, {json_dmg}, {json_xp}, {json_components});')
                        
                        import math
                        perk_count = p_stats.get('perk_count', 0)
                        rows = math.ceil(perk_count / 5) if component_settings["perks"] and perk_count > 0 else 0
                        tier_height = 14 if component_settings["rank"] and p_stats.get("overlay_tier") else 0
                        calc_height = 28 + (rows * 55)
                        if component_settings["damage"]:
                            calc_height += 88
                        if component_settings["rank"]:
                            calc_height += 42 + tier_height
                        if component_settings["xp"]:
                            calc_height += 38
                        if component_settings["progress"]:
                            calc_height += 56
                        calc_height += 12
                        calc_height = max(calc_height, 70)
                        unified_window.resize(
                            get_scaled_overlay_dimension(OVERLAY_BASE_WIDTH),
                            get_scaled_overlay_dimension(calc_height)
                        )
                                
                except Exception as e:
                    print(f"Unified Overlay Error: {e}")
        
        time.sleep(2)

def toggle_overlays_logic(enable):
    global unified_window, stop_overlays
    
    if enable:
        stop_overlays = False
        if unified_window is None:
            unified_window = webview.create_window(
                'BO3 Overlay', 
                html=get_unified_overlay_html(), 
                width=get_scaled_overlay_dimension(OVERLAY_BASE_WIDTH),
                height=get_scaled_overlay_dimension(OVERLAY_BASE_HEIGHT),
                x=50, y=100,
                frameless=True, 
                on_top=True, 
                transparent=False 
            )
        
        t = threading.Thread(target=overlay_loop)
        t.daemon = True
        t.start()
        
    else:
        stop_overlays = True
        if unified_window:
            unified_window.destroy()
            unified_window = None

def push_overlay_theme():
    if not unified_window:
        return
    try:
        unified_window.evaluate_js(f'applyOverlayTheme({json.dumps(get_overlay_theme())});')
    except Exception:
        pass

def push_overlay_scale():
    if not unified_window:
        return
    try:
        unified_window.evaluate_js(f'setOverlayScale({json.dumps(get_overlay_scale())});')
        unified_window.resize(
            get_scaled_overlay_dimension(OVERLAY_BASE_WIDTH),
            get_scaled_overlay_dimension(OVERLAY_BASE_HEIGHT)
        )
    except Exception:
        pass

# --- GRAPH OVERLAY ---
def get_graph_overlay_html():
    chart_js_path = os.path.join(get_base_path(), "chart.js")
    chart_js_content = ""
    try:
        if os.path.exists(chart_js_path):
            with open(chart_js_path, "r", encoding="utf-8") as f:
                chart_js_content = f.read()
    except Exception:
        pass
    return build_graph_overlay_html(
        json.dumps(get_overlay_theme()),
        json.dumps(get_overlay_scale()),
        chart_js_content,
    )


def graph_overlay_loop():
    global graph_overlay_window, stop_graph_overlay

    while not stop_graph_overlay:
        if graph_overlay_window:
            path = app_config.get('live_path')
            if path and os.path.exists(path):
                try:
                    data = load_json(path)
                    stats = process_stats(
                        data,
                        is_live=True,
                        overflow_recovery_enabled=app_config.get('xp_overflow_recovery_enabled', False)
                    )

                    if stats and stats['players']:
                        p_stats = stats['players'][0]
                        overlay_components = app_config.get('overlay_components', {})
                        if not isinstance(overlay_components, dict):
                            overlay_components = {}

                        import math
                        calc_height = 20
                        graph_count = 0
                        for g in ["xpm_graph", "roundxp_graph", "zpm_graph"]:
                            if overlay_components.get(g, False):
                                graph_count += 1
                                calc_height += 110
                        calc_height = max(calc_height, 50)

                        graph_data = {
                            "xpmLabels": p_stats.get("graph_labels", []),
                            "xpmData": p_stats.get("graph_data", []),
                            "roundXpLabels": p_stats.get("round_xp_labels", []),
                            "roundXpData": p_stats.get("round_xp_data", []),
                            "zpmLabels": p_stats.get("zpm_labels", []),
                            "zpmData": p_stats.get("zpm_data", []),
                            "components": {
                                "xpm_graph": overlay_components.get("xpm_graph", False),
                                "roundxp_graph": overlay_components.get("roundxp_graph", False),
                                "zpm_graph": overlay_components.get("zpm_graph", False),
                            }
                        }

                        json_theme = json.dumps(get_overlay_theme())
                        json_scale = json.dumps(get_overlay_scale())
                        graph_overlay_window.evaluate_js(
                            f'applyGraphOverlayTheme({json_theme});'
                            f'setGraphOverlayScale({json_scale});'
                            f'updateGraphOverlay({json.dumps(graph_data)});'
                        )
                        graph_overlay_window.resize(
                            get_scaled_overlay_dimension(280),
                            get_scaled_overlay_dimension(calc_height)
                        )

                except Exception as e:
                    print(f"Graph Overlay Error: {e}")

        time.sleep(2)


def toggle_graph_overlay_logic(enable):
    global graph_overlay_window, stop_graph_overlay

    if enable:
        stop_graph_overlay = False
        if graph_overlay_window is None:
            graph_overlay_window = webview.create_window(
                'BO3 Graph Overlay',
                html=get_graph_overlay_html(),
                width=get_scaled_overlay_dimension(280),
                height=get_scaled_overlay_dimension(100),
                x=350, y=100,
                frameless=True,
                on_top=True,
            )

        t = threading.Thread(target=graph_overlay_loop)
        t.daemon = True
        t.start()

    else:
        stop_graph_overlay = True
        if graph_overlay_window:
            graph_overlay_window.destroy()
            graph_overlay_window = None


def push_graph_overlay_theme():
    if not graph_overlay_window:
        return
    try:
        graph_overlay_window.evaluate_js(f'applyGraphOverlayTheme({json.dumps(get_overlay_theme())});')
    except Exception:
        pass


def push_graph_overlay_scale():
    if not graph_overlay_window:
        return
    try:
        graph_overlay_window.evaluate_js(f'setGraphOverlayScale({json.dumps(get_overlay_scale())});')
    except Exception:
        pass


def get_xp_debugger_html():
    return build_xp_debugger_html()


def _publish_xp_debug_rows():
    global xp_debug_window
    if not xp_debug_window:
        return
    try:
        with xp_debug_lock:
            rows = list(xp_debug_rows)
        xp_debug_window.evaluate_js(f"updateXpDebug({json.dumps(rows)})")
    except Exception:
        pass

def record_xp_debug(snapshot, current_round, current_time, map_name="Unknown"):
    if not app_config.get('xp_debugger_enabled', False) or not snapshot:
        return

    game_id = str(snapshot.get("game_id", "unknown"))
    player_id = str(snapshot.get("player_id", "0"))
    current_round = int(current_round)
    total_match_xp = int(snapshot.get("total_match_xp", 0))
    key = f"{game_id}|{player_id}|{current_round}"

    with xp_debug_lock:
        previous_round_totals = [
            int(row.get("total_match_xp", 0))
            for row in xp_debug_rows
            if row.get("game_id") == game_id
            and row.get("player_id") == player_id
            and int(row.get("round", 0)) < current_round
        ]
        previous_round_total = previous_round_totals[-1] if previous_round_totals else 0
        round_xp = total_match_xp - previous_round_total
        if round_xp < 0:
            round_xp = 0

        previous_level = snapshot.get("previous_level")
        previous_prestige = snapshot.get("previous_prestige")
        previous_legend = snapshot.get("previous_prestige_legend")
        previous_absolute = snapshot.get("previous_prestige_absolute")
        previous_ultimate = snapshot.get("previous_prestige_ultimate")
        prestige = snapshot.get("prestige")
        legend = snapshot.get("prestige_legend", 0)
        absolute = snapshot.get("prestige_absolute", 0)
        ultimate = snapshot.get("prestige_ultimate", 0)
        level = snapshot.get("level")
        rank_changed = (
            previous_level is not None
            and (
                previous_level != level
                or previous_prestige != prestige
                or previous_legend != legend
                or previous_absolute != absolute
                or previous_ultimate != ultimate
            )
        )
        rank_change_label = ""
        if rank_changed:
            rank_change_label = (
                f"U{previous_ultimate} A{previous_absolute} G{previous_legend} "
                f"P{previous_prestige} L{previous_level} -> "
                f"U{ultimate} A{absolute} G{legend} P{prestige} L{level}"
            )

        rollover = snapshot.get("rollover_debug") or {}
        recovery = snapshot.get("recovery_debug") or {}
        xp_math_label = ""
        if rollover:
            remaining = int(rollover.get("remaining_previous_level", 0))
            skipped = int(rollover.get("skipped_level_xp", 0))
            current_progress = int(rollover.get("current_level_progress", 0))
            parts = [f"{remaining:,} remaining"]
            if skipped:
                parts.append(f"{skipped:,} skipped")
            parts.append(f"{current_progress:,} level XP")
            xp_math_label = " + ".join(parts)
        if recovery:
            reason = recovery.get("reason", "unstable XP snapshot")
            pending_count = int(recovery.get("pending_count", 0))
            if recovery.get("recovered"):
                recovery_label = f"RECOVERED estimate after {pending_count} unstable tick(s): {reason}"
            else:
                recovery_label = f"IGNORED unstable XP tick {pending_count}: {reason}"
            xp_math_label = f"{xp_math_label} | {recovery_label}" if xp_math_label else recovery_label

        row = {
            "key": key,
            "updated_at": time.strftime("%H:%M:%S"),
            "game_id": game_id,
            "short_game_id": game_id[-18:] if len(game_id) > 18 else game_id,
            "map_name": str(map_name).replace("_", " ").title(),
            "player_id": player_id,
            "round": current_round,
            "time_total": int(current_time),
            "ultimate": ultimate,
            "absolute": absolute,
            "legend": legend,
            "prestige": prestige,
            "level": level,
            "current_xp": snapshot.get("current_xp", 0),
            "tick_xp": snapshot.get("tick_xp", 0),
            "round_xp": round_xp,
            "total_match_xp": total_match_xp,
            "rank_changed": rank_changed,
            "xp_recovery": bool(recovery),
            "xp_math_label": xp_math_label,
            "rank_change_label": rank_change_label
        }

        replaced = False
        for idx, existing in enumerate(xp_debug_rows):
            if existing.get("key") == key:
                xp_debug_rows[idx] = row
                replaced = True
                break
        if not replaced:
            xp_debug_rows.append(row)

        del xp_debug_rows[:-250]

    _publish_xp_debug_rows()

def toggle_xp_debugger_logic(enable):
    global xp_debug_window
    if enable:
        if xp_debug_window:
            _publish_xp_debug_rows()
            return
        try:
            xp_debug_window = webview.create_window(
                'BO3 XP Debugger',
                html=get_xp_debugger_html(),
                width=1100,
                height=520,
                resizable=True
            )
            threading.Timer(0.5, _publish_xp_debug_rows).start()
        except Exception as e:
            print(f"XP Debugger Error: {e}")
    else:
        try:
            if xp_debug_window:
                xp_debug_window.destroy()
        except Exception:
            pass
        xp_debug_window = None

# --- SETUP SCREEN HTML (INSERTED) ---
def get_setup_html():
    return build_setup_html(load_css(CSS_SETUP_FILE))

# --- UNIFIED DASHBOARD HTML ---
def get_main_app_html():
    chart_js_path = os.path.join(get_base_path(), "chart.js")
    chart_js_content = ""
    try:
        if os.path.exists(chart_js_path):
            with open(chart_js_path, "r", encoding="utf-8") as f:
                chart_js_content = f.read()
    except Exception:
        pass
    return build_main_app_html(
        load_css(CSS_MAIN_FILE),
        app_config,
        APP_VERSION,
        GLOBAL_STATS_PROMPT_VERSION,
        chart_js_content,
    )

# --- MAP COMPATIBILITY LAUNCHER ---
def launch_map_compat_window():
    compat_dir = os.path.join(get_base_path(), "local map compatiblityu")
    compat_exe = os.path.join(compat_dir, "UEMMapCompatibility.exe")
    app_script = os.path.join(compat_dir, "app.py")
    if os.path.exists(compat_exe):
        launch_target = [compat_exe]
    elif os.path.exists(app_script):
        launch_target = [sys.executable, app_script]
    else:
        return False
    try:
        subprocess.Popen(launch_target, cwd=compat_dir, close_fds=True)
        return True
    except Exception:
        return False


def _write_tracker_config_backup(save_path):
    config_dir = get_config_dir()
    save_path = normalize_backup_path(save_path)
    files_added = 0

    with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        manifest = {
            "app": "BO3 Tracker",
            "version": APP_VERSION,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config_dir": config_dir,
            "files": [],
        }
        for root, dirs, files in os.walk(config_dir):
            dirs[:] = [d for d in dirs if d != "workshop_image_cache"]
            for fname in files:
                fpath = os.path.join(root, fname)
                if os.path.abspath(fpath) == os.path.abspath(save_path):
                    continue
                rel = os.path.relpath(fpath, config_dir)
                arcname = os.path.join("config", rel).replace("\\", "/")
                zipf.write(fpath, arcname)
                manifest["files"].append(arcname)
                files_added += 1

        readme = (
            "BO3 Tracker local config backup\n\n"
            "This archive contains local tracker config/progress files from the config folder.\n"
            "It is intended for recovery if the tracker config breaks or progress files are damaged.\n\n"
            "Use Restore Tracker Config Backup inside BO3 Tracker to restore this archive.\n\n"
            "Workshop image cache files are not included because they can be regenerated.\n"
        )
        zipf.writestr("README_RESTORE.txt", readme)
        zipf.writestr("backup_manifest.json", json.dumps(manifest, indent=2))

    return files_added


def _safe_config_member(filename):
    normalized = filename.replace("\\", "/")
    if not normalized.startswith("config/"):
        return None

    rel = normalized[len("config/"):].strip("/")
    if not rel or rel.startswith("/") or rel.startswith("\\"):
        return None

    parts = [part for part in rel.split("/") if part]
    if any(part in (".", "..") for part in parts):
        return None
    if parts and parts[0] == "workshop_image_cache":
        return None

    return os.path.join(*parts)


def _restore_tracker_config_backup(zip_path):
    global app_config

    if not zip_path or not zipfile.is_zipfile(zip_path):
        raise ValueError("Selected file is not a valid zip archive.")

    config_dir = get_config_dir()
    members = []
    with zipfile.ZipFile(zip_path, "r") as zipf:
        for info in zipf.infolist():
            if info.is_dir():
                continue
            rel = _safe_config_member(info.filename)
            if rel:
                members.append((info, rel))

    if not members:
        raise ValueError("No BO3 Tracker config files were found in the selected backup.")

    existing_files = []
    for _, rel in members:
        target = os.path.abspath(os.path.join(config_dir, rel))
        if os.path.exists(target):
            existing_files.append(target)

    safety_backup = ""
    if existing_files:
        backups_dir = os.path.join(get_base_path(), "Backups")
        os.makedirs(backups_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safety_backup = os.path.join(backups_dir, f"tracker_config_before_restore_{timestamp}.zip")
        _write_tracker_config_backup(safety_backup)

    config_abs = os.path.abspath(config_dir)
    restored = []
    with zipfile.ZipFile(zip_path, "r") as zipf:
        for info, rel in members:
            target = os.path.abspath(os.path.join(config_dir, rel))
            if os.path.commonpath([config_abs, target]) != config_abs:
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zipf.open(info, "r") as src, open(target, "wb") as dst:
                dst.write(src.read())
            restored.append(target)

    restored_config = load_json(get_runtime_path(CONFIG_FILE)) or {}
    app_config = restored_config if isinstance(restored_config, dict) else {}
    return {
        "config_dir": config_dir,
        "restored": restored,
        "safety_backup": safety_backup,
        "configured": bool(app_config.get("live_path")),
    }

# --- API MIXINS ---
from api_display import DisplayAPI
from api_data import DataAPI
from api_network import NetworkAPI
from api_system import SystemAPI

# --- API CLASS ---
class TrackerAPI(DisplayAPI, DataAPI, NetworkAPI, SystemAPI):
    def __init__(self):
        self.last_user_path = None

def get_player_weapon_snapshot(player):
    if not isinstance(player, dict):
        return {}
    for key in ("weapon_data", "top5"):
        weapons = player.get(key, {})
        if isinstance(weapons, dict) and weapons:
            return weapons
    return {}

def merge_weapon_snapshot(match_weapon_cache, game_id, player_id, player):
    if not isinstance(player, dict):
        return

    cache_key = (str(game_id), str(player_id))
    cached_weapons = match_weapon_cache.setdefault(cache_key, {})
    current_weapons = get_player_weapon_snapshot(player)

    for weapon_id, weapon in current_weapons.items():
        if not isinstance(weapon, dict):
            continue

        weapon_id = str(weapon_id)
        cached = cached_weapons.setdefault(weapon_id, dict(weapon))
        for field in ("kills", "headshots", "damage"):
            try:
                cached[field] = max(int(float(cached.get(field, 0) or 0)), int(float(weapon.get(field, 0) or 0)))
            except:
                if field not in cached:
                    cached[field] = weapon.get(field, 0)

        for field, value in weapon.items():
            if field not in cached or cached.get(field) in ("", None, "none", "Unknown"):
                cached[field] = value

        try:
            cached["repack_level"] = max(int(cached.get("repack_level", 0) or 0), int(weapon.get("repack_level", 0) or 0))
        except:
            pass
        try:
            cached["enchant"] = max(int(cached.get("enchant", 0) or 0), int(weapon.get("enchant", 0) or 0))
        except:
            pass
        current_aat = weapon.get("currentAAT") or weapon.get("current_aat") or weapon.get("aat")
        if current_aat not in ("", None, "none", "None", "null", "0"):
            cached["currentAAT"] = current_aat

    if cached_weapons:
        player["weapon_data"] = cached_weapons

def _safe_int(value, default=0):
    try:
        return int(str(value).replace(",", "").strip())
    except:
        return default

def update_live_score_points(session_score, session_last_score, session_round_log, player_id, player, game):
    current_score = _safe_int(player.get("points", 0))
    current_round = _safe_int(game.get("rounds_total", player.get("round", 0)))
    current_time = _safe_int(game.get("time_total", 0))

    if player_id not in session_score:
        session_score[player_id] = 0
        session_last_score[player_id] = current_score
        session_round_log[player_id] = {}
    else:
        last_score = session_last_score.get(player_id, current_score)
        if current_score > last_score:
            session_score[player_id] += current_score - last_score
        session_last_score[player_id] = current_score

    round_key = str(current_round)
    session_round_log.setdefault(player_id, {})[round_key] = {
        "round": current_round,
        "time": current_time,
        "score": current_score,
        "earned": session_score[player_id],
    }

    player["live_score_points_earned"] = session_score[player_id]
    player["score_round_history"] = session_round_log[player_id]
    return session_score[player_id]

# --- LIVE BACKGROUND LOGIC (MULTI-PLAYER) ---
def monitor_game():
    last_saved_data_str = ""  
    last_game_id = None
    known_active_perks = {} 
    session_perk_count = {} 
    
    # Simple live trackers
    session_score = {}
    session_last_score = {}
    session_score_round_log = {}
    
    session_match_box = {}
    session_last_raw_box = {}
    session_weapon_cache = {}

    while True:
        live_path = app_config.get('live_path')
        hist_path = app_config.get('history_path')
        
        if not live_path or not hist_path: 
            time.sleep(5)
            continue
            
        try:
            if os.path.exists(live_path):
                current_data = load_json(live_path)
                
                if current_data:
                    game = current_data.get('game') or current_data.get('data', {}).get('game', {})
                    raw_id = str(game.get('game_id', '0'))
                    
                    if raw_id and raw_id != "0":
                        if raw_id != last_game_id:
                            last_game_id = raw_id
                            known_active_perks = {}
                            session_perk_count = {}
                            
                            # Reset our live tracker when a completely new game starts
                            session_score = {}
                            session_last_score = {}
                            session_score_round_log = {}
                            session_match_box = {}
                            session_last_raw_box = {}
                            session_weapon_cache = {}
                        
                        players = current_data.get('players') or current_data.get('data', {}).get('players', {})
                        if players:
                            for pid, p in players.items():
                                # --- 1. PERK LOGIC ---
                                if pid not in known_active_perks:
                                    known_active_perks[pid] = set()
                                    session_perk_count[pid] = 0

                                raw_perks = p.get('perks', [])
                                if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
                                current_perks_set = set([x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x])
                                new_perks = current_perks_set - known_active_perks[pid]
                                if new_perks: session_perk_count[pid] += len(new_perks)
                                if len(current_perks_set) == 0 and len(known_active_perks[pid]) > 0:
                                    known_active_perks[pid] = set()
                                else:
                                    known_active_perks[pid] |= current_perks_set
                                p['calculated_perks_drank'] = session_perk_count[pid]
                                
                                # --- 2. SIMPLE DROP-DETECTION TRACKER ---
                                current_raw_box = int(p.get('mystery_box_used', 0))
                                
                                if pid not in session_match_box:
                                    session_match_box[pid] = current_raw_box
                                    session_last_raw_box[pid] = current_raw_box
                                
                                update_live_score_points(session_score, session_last_score, session_score_round_log, pid, p, game)
                                
                                # Box Math
                                last_raw_box = session_last_raw_box[pid]
                                if current_raw_box > last_raw_box:
                                    session_match_box[pid] += (current_raw_box - last_raw_box)
                                elif current_raw_box < last_raw_box:
                                    # DROP DETECTED!
                                    session_match_box[pid] += current_raw_box
                                session_last_raw_box[pid] = current_raw_box
                                
                                # Save the clean values
                                p['true_match_points'] = p.get('live_score_points_earned', 0)
                                p['true_match_box'] = session_match_box[pid]
                                merge_weapon_snapshot(session_weapon_cache, raw_id, pid, p)

                                # Calculate match XP before feeding live data to challenge system
                                p_prest = int(p.get('prestige', 0))
                                p_lvl = int(p.get('level', 1))
                                p_xp = int(p.get('xp', p.get('total_xp', 0)))
                                p_leg = int(p.get('prestige_legend', 0))
                                p_abso = int(p.get('prestige_absolute', 0))
                                p_ult = int(p.get('prestige_ultimate', 0))
                                p['match_xp_earned'] = xp_tracker_instance.calculate_match_xp(
                                    raw_id, pid, p_prest, p_lvl, p_xp, p_leg,
                                    app_config.get('xp_overflow_recovery_enabled', False), p_abso, p_ult
                                )
                                p['total_levels_gained'] = xp_tracker_instance.get_total_levels_gained(raw_id, pid)

                                # Feed live data to challenge system (incremental updates during match)
                                challenge_manager.apply_live_update(raw_id, p, game)

                        # Discover map weapons from all players
                        map_weapons_manager.discover_from_game(current_data)
                        schedule_map_weapons_push("gameplay")
                        schedule_discord_presence_update(current_data)

                        # --- SAVE LOGIC ---
                        current_data_str = json.dumps(current_data, sort_keys=True)
                        if current_data_str != last_saved_data_str:
                            safe_id = sanitize_filename(raw_id)
                            if os.path.exists(hist_path):
                                target_file = os.path.join(hist_path, f"Game_{safe_id}.json")
                                
                                game_info = current_data.get('game') or current_data.get('data', {}).get('game', {})
                                g_id = str(game_info.get('game_id', 'unknown'))
                                p_dict = current_data.get('players') or current_data.get('data', {}).get('players', {})
                                
                                for pid_key, p_data in p_dict.items():
                                    p_prest = int(p_data.get('prestige', 0))
                                    p_lvl = int(p_data.get('level', 1))
                                    p_xp = int(p_data.get('xp', p_data.get('total_xp', 0)))
                                    p_leg = int(p_data.get('prestige_legend', 0))
                                    p_abso = int(p_data.get('prestige_absolute', 0))
                                    p_ult = int(p_data.get('prestige_ultimate', 0))
                                    p_data['match_xp_earned'] = xp_tracker_instance.calculate_match_xp(
                                        g_id, pid_key, p_prest, p_lvl, p_xp, p_leg,
                                        app_config.get('xp_overflow_recovery_enabled', False), p_abso, p_ult
                                    )
                                    # --- NEW: UPDATE & INJECT XPM HISTORY ---
                                    current_round = int(game_info.get('rounds_total', 0))
                                    current_time = int(game_info.get('time_total', 0))
                                    try:
                                        current_zpm = float(game_info.get('zpm', 0))
                                    except:
                                        current_zpm = 0
                                    map_name = game_info.get('map_played', 'Unknown')
                                    xp_debug_snapshot = xp_tracker_instance.get_last_debug_snapshot(g_id, pid_key)
                                    record_xp_debug(xp_debug_snapshot, current_round, current_time, map_name)
                                    p_data['round_history'] = xpm_grapher_instance.update_live_data(
                                        g_id, pid_key, current_round, current_time, p_data['match_xp_earned'], current_zpm
                                    )
                                
                                if save_json(target_file, current_data):
                                    last_saved_data_str = current_data_str
                                    schedule_global_stats_sync("archive-save", force=False)
        except Exception:
            pass
        
        time.sleep(2)

def get_entry_point_html():
    if not app_config or not app_config.get('live_path'):
        return get_setup_html()
    return get_main_app_html()

def on_closed():
    toggle_overlays_logic(False)
    toggle_graph_overlay_logic(False)
    toggle_xp_debugger_logic(False)
    clear_discord_presence()
    os._exit(0)

def startup_checks():
    refresh_remote_management()
    apply_remote_management()
    configure_discord_presence()
    if app_config.get('overlays_enabled', False):
        toggle_overlays_logic(True)
    if app_config.get('graph_overlay_enabled', False):
        toggle_graph_overlay_logic(True)
    if app_config.get('xp_debugger_enabled', False):
        toggle_xp_debugger_logic(True)
    schedule_global_stats_sync("startup", force=False)
    schedule_custom_camos_sync("startup", force=False)
    schedule_map_weapons_startup_sync()
    schedule_map_challenges_sync("startup", force=False)

if __name__ == "__main__":
    sys.modules["bo3tracker"] = sys.modules["__main__"]
    migrate_all_runtime_paths()
    config_path = get_runtime_path(CONFIG_FILE)
    if os.path.exists(config_path):
        app_config = load_json(config_path) or {}
    
    t = threading.Thread(target=monitor_game)
    t.daemon = True
    t.start()
    
    api = TrackerAPI()
    window = webview.create_window('BO3 Tracker & Camo Matrix', html=get_entry_point_html(), width=1300, height=900, background_color='#0b0c10', js_api=api)
    
    window.events.closed += on_closed
    webview.start(func=startup_checks)
