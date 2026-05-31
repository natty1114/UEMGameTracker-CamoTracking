import base64
import glob
import json
import os
import sys
import threading
import time
import zipfile

from app_paths import get_base_path, get_config_dir, get_runtime_path
_bt = lambda: sys.modules["bo3tracker"]
from asset_helpers import load_css
from file_utils import load_json, save_json
from game_data import CONFIG_FILE, CSS_SETUP_FILE
from overlay_themes import (
    OVERLAY_BASE_HEIGHT,
    OVERLAY_BASE_WIDTH,
    OVERLAY_SIZE_DEFAULT,
    OVERLAY_SIZE_MAX,
    OVERLAY_SIZE_MIN,
)
from player_stats_backup import (

    create_player_stats_backup,
    find_player_stats_files,
    normalize_backup_path,
    restore_player_stats_backup,
)


class SystemAPI:
    def get_startup_asset_status(self):
        return _bt().get_hosted_reward_sync_status()

    def get_diagnostics_status(self):
        def fmt_time(ts):
            try:
                ts = int(float(ts or 0))
            except (TypeError, ValueError):
                ts = 0
            if ts <= 0:
                return "Never"
            return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

        def row(key, label, status, detail):
            return {
                "key": key,
                "label": label,
                "status": status,
                "detail": str(detail or ""),
            }

        rows = []
        cfg = _bt().app_config

        live_path = str(cfg.get("live_path") or "").strip()
        sync_enabled = bool(cfg.get("currentgame_sync_enabled", False))
        sync_mode = str(cfg.get("currentgame_sync_mode", "off") or "off")
        try:
            live_data = _bt().get_live_game_data()
        except Exception:
            live_data = None
        if live_data:
            game = live_data.get("game") or live_data.get("data", {}).get("game", {})
            game_id = str(game.get("game_id") or "live data")
            rows.append(row("live", "Live Game", "ok", f"CurrentGame readable ({game_id})."))
        elif sync_enabled and sync_mode != "off":
            rows.append(row("live", "Live Game", "warn", f"Sync {sync_mode}: {_bt().currentgame_sync_manager.status()}"))
        elif live_path:
            rows.append(row("live", "Live Game", "bad", "CurrentGame.json path is set but not readable."))
        else:
            rows.append(row("live", "Live Game", "warn", "CurrentGame.json path is not configured."))

        hist_path = str(cfg.get("history_path") or "").strip()
        if hist_path and os.path.isdir(hist_path):
            files = glob.glob(os.path.join(hist_path, "Game_*.json"))
            latest = max((os.path.getmtime(path) for path in files), default=0)
            rows.append(row("history", "History", "ok", f"{len(files)} archived matches. Latest: {fmt_time(latest)}."))
        elif hist_path:
            rows.append(row("history", "History", "bad", "History folder is set but not reachable."))
        else:
            rows.append(row("history", "History", "warn", "History folder is not configured."))

        xp_path = get_runtime_path("match_xp_cache.json")
        xp_cache = load_json(xp_path) if os.path.exists(xp_path) else {}
        if isinstance(xp_cache, dict) and xp_cache:
            rows.append(row("xp", "XP Cache", "ok", f"{len(xp_cache)} cached match XP entries."))
        elif os.path.exists(xp_path):
            rows.append(row("xp", "XP Cache", "warn", "XP cache exists but has no match entries yet."))
        else:
            rows.append(row("xp", "XP Cache", "warn", "XP cache has not been created yet."))

        challenge_path = get_runtime_path("challenges.json")
        map_challenge_msg = str(cfg.get("map_challenges_last_sync_msg") or cfg.get("map_challenges_last_result") or "").strip()
        if os.path.exists(challenge_path):
            detail = f"Local progress file present. {map_challenge_msg}".strip()
            rows.append(row("challenges", "Challenges", "ok", detail))
        else:
            rows.append(row("challenges", "Challenges", "warn", map_challenge_msg or "Challenge progress file has not been created yet."))

        global_enabled = bool(cfg.get("global_stats_enabled", False))
        global_msg = str(cfg.get("global_stats_last_message") or cfg.get("global_stats_last_error") or "").strip()
        global_sync = fmt_time(cfg.get("global_stats_last_sync"))
        global_result = cfg.get("global_stats_last_result")
        if not isinstance(global_result, dict):
            global_result = {}
        if not global_enabled:
            rows.append(row("global", "Global Stats", "off", "Uploads are disabled."))
        elif cfg.get("global_stats_last_error") and not global_result.get("ok"):
            rows.append(row("global", "Global Stats", "bad", global_msg or "Last sync failed."))
        elif cfg.get("global_stats_last_sync"):
            rows.append(row("global", "Global Stats", "ok", f"Last sync: {global_sync}. {global_msg}".strip()))
        else:
            rows.append(row("global", "Global Stats", "warn", "Enabled but not synced yet."))

        reward_status = _bt().get_hosted_reward_sync_status()
        if reward_status.get("error"):
            reward_state = "bad"
        elif reward_status.get("running"):
            reward_state = "warn"
        elif reward_status.get("done"):
            reward_state = "ok"
        else:
            reward_state = "off"
        reward_detail = reward_status.get("message") or "Waiting to sync hosted rewards."
        total = int(reward_status.get("total") or 0)
        current = int(reward_status.get("current") or 0)
        if total > 0:
            reward_detail = f"{reward_detail} ({min(current, total)} / {total})"
        rows.append(row("rewards", "Reward Assets", reward_state, reward_detail))

        return {"rows": rows, "updated_at": fmt_time(time.time())}

    # --- Config ---
    def save_config(self, live, hist):
        _bt().app_config['live_path'] = live
        _bt().app_config['history_path'] = hist
        _bt().app_config['currentgame_sync_enabled'] = False
        _bt().app_config['currentgame_sync_mode'] = 'off'
        _bt().save_app_config()
        _bt().currentgame_sync_manager.apply_config(_bt().app_config)
        t = threading.Timer(0.1, _bt().window.load_html, args=(_bt().get_main_app_html(),))
        t.start()
        return True

    def save_remote_sync_config(self, host_url, password, hist, selected_player=""):
        return {
            "success": False,
            "msg": "LAN CurrentGame sync has been removed. Use website relay sync instead.",
        }

    def save_remote_relay_sync_config(self, password, hist, relay_url="", selected_player=""):
        _bt().app_config['live_path'] = ''
        _bt().app_config['history_path'] = str(hist or "").strip()
        _bt().app_config['currentgame_sync_enabled'] = True
        _bt().app_config['currentgame_sync_mode'] = 'relay_client'
        _bt().app_config['currentgame_sync_password'] = str(password or "").strip()
        _bt().app_config['currentgame_sync_selected_player'] = str(selected_player or "").strip()
        _bt().app_config['currentgame_relay_url'] = str(relay_url or _bt().CURRENTGAME_RELAY_URL or "").strip()
        _bt().save_app_config()
        _bt().currentgame_sync_manager.apply_config(_bt().app_config)
        t = threading.Timer(0.1, _bt().window.load_html, args=(_bt().get_main_app_html(),))
        t.start()
        return True

    def reset_config(self):
        _bt().currentgame_sync_manager.stop_host()
        _bt().currentgame_sync_manager.stop_relay_host(_bt().app_config)
        _bt().app_config = {}
        save_json(get_runtime_path(CONFIG_FILE), {})
        return True

    def launch_setup(self):
        t = threading.Timer(0.1, _bt().window.load_html, args=(_bt().get_setup_html(),))
        t.start()
        return True

    def launch_dashboard(self):
        return True

    def save_live_capture(self, data_url, suggested_name="bo3_tracker_live_capture.png"):
        if not isinstance(data_url, str) or not data_url.startswith("data:image/png;base64,"):
            return {"success": False, "msg": "Capture image data was invalid."}

        safe_name = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in str(suggested_name or "")).strip()
        if not safe_name:
            safe_name = "bo3_tracker_live_capture.png"
        if not safe_name.lower().endswith(".png"):
            safe_name += ".png"

        save_result = _bt().window.create_file_dialog(
            _bt().webview.FileDialog.SAVE,
            save_filename=safe_name,
            file_types=("PNG Image (*.png)",)
        )
        if not save_result:
            return {"success": False, "msg": "Capture cancelled."}

        save_path = save_result[0] if isinstance(save_result, (tuple, list)) else save_result
        if not str(save_path).lower().endswith(".png"):
            save_path = str(save_path) + ".png"

        try:
            raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
            with open(save_path, "wb") as handle:
                handle.write(raw)
            return {"success": True, "msg": f"Saved live capture to {save_path}", "path": save_path}
        except Exception as e:
            return {"success": False, "msg": f"Could not save capture: {str(e)}"}

    # --- File Dialogs ---
    def browse_live_file(self):
        result = _bt().window.create_file_dialog(_bt().webview.FileDialog.OPEN, allow_multiple=False, file_types=('JSON Files (*.json)',))
        return result[0] if result else None

    def browse_history_folder(self):
        result = _bt().window.create_file_dialog(_bt().webview.FileDialog.FOLDER)
        return result[0] if result else None

    def browse_user_json(self):
        result = _bt().window.create_file_dialog(_bt().webview.FileDialog.OPEN, allow_multiple=False, file_types=('JSON Files (*.json)',))
        if result:
            self.last_user_path = result[0]
            return result[0]
        return None

    def open_map_compat(self):
        return {
            "ok": False,
            "msg": "Map Compat is temporarily disabled until Steam Workshop image download scripts are fixed.",
        }

    # --- CurrentGame Sync ---
    def get_currentgame_sync_settings(self):
        mode = str(_bt().app_config.get("currentgame_sync_mode", "off") or "off").lower()
        if mode not in ("relay_host", "relay_client"):
            mode = "off"
        return {
            "enabled": bool(_bt().app_config.get("currentgame_sync_enabled", False)) and mode != "off",
            "mode": mode,
            "relay_url": str(_bt().app_config.get("currentgame_relay_url", _bt().CURRENTGAME_RELAY_URL) or ""),
            "selected_player": str(_bt().app_config.get("currentgame_sync_selected_player", "") or ""),
            "status": _bt().currentgame_sync_manager.status(),
        }

    def save_currentgame_sync_settings(self, enabled, mode, host_url="", password="", port=31715, selected_player="", relay_url=""):
        was_relay_host = _bt().currentgame_sync_manager.is_relay_host_enabled(_bt().app_config)
        clean_mode = str(mode or "off").strip().lower()
        if clean_mode not in ("off", "relay_host", "relay_client"):
            clean_mode = "off"

        _bt().app_config["currentgame_sync_enabled"] = bool(enabled) and clean_mode != "off"
        _bt().app_config["currentgame_sync_mode"] = clean_mode
        _bt().app_config["currentgame_relay_url"] = str(relay_url or _bt().CURRENTGAME_RELAY_URL or "").strip()
        if password:
            _bt().app_config["currentgame_sync_password"] = str(password or "").strip()
        _bt().app_config["currentgame_sync_selected_player"] = str(selected_player or "").strip()
        if not _bt().app_config["currentgame_sync_enabled"]:
            _bt().app_config["currentgame_sync_mode"] = "off"
            if was_relay_host:
                _bt().currentgame_sync_manager.stop_relay_host(_bt().app_config)
        _bt().save_app_config()
        result = _bt().currentgame_sync_manager.apply_config(_bt().app_config)
        return result

    def get_currentgame_sync_players(self):
        return _bt().currentgame_sync_manager.fetch_client_players(_bt().app_config)

    def discover_currentgame_sync_host(self, password="", port=31715):
        return _bt().currentgame_sync_manager.discover_host(password, port)

    # --- Overlay ---
    def toggle_overlay_system(self, enabled):
        _bt().app_config['overlays_enabled'] = enabled
        _bt().save_app_config()
        t = threading.Thread(target=_bt().toggle_overlays_logic, args=(enabled,))
        t.start()
        return True

    def toggle_overlay_component(self, component, enabled):
        allowed = {"perks", "damage", "rank", "xp", "progress",
                    "xpm_graph", "roundxp_graph", "zpm_graph"}
        if component not in allowed:
            return False
        overlay_components = _bt().app_config.get('overlay_components')
        if not isinstance(overlay_components, dict):
            overlay_components = {}
        overlay_components[component] = bool(enabled)
        _bt().app_config['overlay_components'] = overlay_components
        _bt().save_app_config()
        return True

    def toggle_graph_overlay_system(self, enabled):
        _bt().app_config['graph_overlay_enabled'] = enabled
        _bt().save_app_config()
        t = threading.Thread(target=_bt().toggle_graph_overlay_logic, args=(enabled,))
        t.start()
        return True

    def toggle_graph_overlay_component(self, component, enabled):
        allowed = {"xpm_graph", "roundxp_graph", "zpm_graph"}
        if component not in allowed:
            return False
        overlay_components = _bt().app_config.get('overlay_components')
        if not isinstance(overlay_components, dict):
            overlay_components = {}
        overlay_components[component] = bool(enabled)
        _bt().app_config['overlay_components'] = overlay_components
        _bt().save_app_config()
        return True

    def get_challenge_overlay_settings(self):
        return {
            "enabled": bool(_bt().app_config.get("challenge_overlay_enabled", False)),
            "selected_ids": _bt().normalise_challenge_overlay_ids(
                _bt().app_config.get("challenge_overlay_selected_ids", [])
            ),
        }

    def toggle_challenge_overlay_system(self, enabled):
        _bt().app_config["challenge_overlay_enabled"] = bool(enabled)
        _bt().save_app_config()
        t = threading.Thread(target=_bt().toggle_challenge_overlay_logic, args=(bool(enabled),))
        t.start()
        return True

    def set_challenge_overlay_selection(self, selected_ids):
        selected = _bt().set_challenge_overlay_selection(selected_ids)
        return {"success": True, "selected_ids": selected}

    def set_overlay_size(self, size_percent):
        try:
            value = int(float(size_percent))
        except (TypeError, ValueError):
            value = OVERLAY_SIZE_DEFAULT
        value = max(OVERLAY_SIZE_MIN, min(OVERLAY_SIZE_MAX, value))
        _bt().app_config["overlay_size_percent"] = value
        _bt().save_app_config()
        _bt().push_overlay_scale()
        return {"success": True, "overlay_size_percent": value}

    def get_overlay_size(self):
        return _bt().get_overlay_size_percent()

    # --- XP Debugger ---
    def toggle_xp_debugger(self, enabled):
        _bt().app_config['xp_debugger_enabled'] = enabled
        _bt().save_app_config()
        t = threading.Thread(target=_bt().toggle_xp_debugger_logic, args=(enabled,))
        t.start()
        return True

    def toggle_xp_overflow_recovery(self, enabled):
        _bt().app_config['xp_overflow_recovery_enabled'] = bool(enabled)
        _bt().save_app_config()
        return True

    # --- Backup / Restore (Player Stats) ---
    def backup_player_stats(self):
        live_path = _bt().app_config.get('live_path')
        if not live_path or not os.path.exists(live_path):
            return {"success": False, "msg": "Live Game Path not configured or file not found."}

        players_dir, files_to_backup = find_player_stats_files(live_path)

        if not files_to_backup:
            return {"success": False, "msg": f"No stats_zm_*.cgp files found in the folder ({players_dir})."}

        save_result = _bt().window.create_file_dialog(
            _bt().webview.FileDialog.SAVE,
            save_filename='uem_stats_backup.zip',
            file_types=('ZIP Archives (*.zip)',)
        )

        if not save_result:
            return {"success": False, "msg": "Backup cancelled by user."}

        save_path = save_result[0] if isinstance(save_result, tuple) else save_result
        save_path = normalize_backup_path(save_path)

        try:
            create_player_stats_backup(files_to_backup, save_path)
            return {"success": True, "msg": f"Successfully backed up {len(files_to_backup)} files to {save_path}"}
        except Exception as e:
            return {"success": False, "msg": f"Error creating zip file: {str(e)}"}

    def restore_player_stats(self, live_path_override=None):
        live_path = str(live_path_override or _bt().app_config.get('live_path') or "").strip()
        if not live_path or not os.path.exists(live_path):
            return {"success": False, "msg": "Select or configure CurrentGame.json before restoring UEM stats."}

        open_result = _bt().window.create_file_dialog(
            _bt().webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=('ZIP Archives (*.zip)',)
        )

        if not open_result:
            return {"success": False, "msg": "Restore cancelled by user."}

        zip_path = open_result[0] if isinstance(open_result, (tuple, list)) else open_result

        try:
            result = restore_player_stats_backup(zip_path, live_path)
            safety = f" A safety backup was created at {result['safety_backup']}." if result.get("safety_backup") else ""
            return {
                "success": True,
                "msg": f"Restored {len(result['restored'])} UEM stat files to {result['players_dir']}.{safety}",
            }
        except Exception as e:
            return {"success": False, "msg": f"Error restoring UEM stats backup: {str(e)}"}

    # --- Backup / Restore (Tracker Config) ---
    def backup_tracker_config(self):
        config_dir = get_config_dir()
        if not os.path.isdir(config_dir):
            return {"success": False, "msg": "Tracker config folder could not be found."}

        save_result = _bt().window.create_file_dialog(
            _bt().webview.FileDialog.SAVE,
            save_filename='bo3_tracker_config_backup.zip',
            file_types=('ZIP Archives (*.zip)',)
        )

        if not save_result:
            return {"success": False, "msg": "Backup cancelled by user."}

        save_path = save_result[0] if isinstance(save_result, tuple) else save_result
        save_path = normalize_backup_path(save_path)

        try:
            files_added = _bt()._write_tracker_config_backup(save_path)
            if files_added == 0:
                return {"success": False, "msg": "No tracker config files were found to back up."}
            return {"success": True, "msg": f"Successfully backed up {files_added} tracker config files to {save_path}"}
        except Exception as e:
            return {"success": False, "msg": f"Error creating tracker config backup: {str(e)}"}

    def restore_tracker_config(self, reload_after=True):
        open_result = _bt().window.create_file_dialog(
            _bt().webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=('ZIP Archives (*.zip)',)
        )

        if not open_result:
            return {"success": False, "msg": "Restore cancelled by user."}

        zip_path = open_result[0] if isinstance(open_result, (tuple, list)) else open_result

        try:
            result = _bt()._restore_tracker_config_backup(zip_path)
            safety = f" A safety backup was created at {result['safety_backup']}." if result.get("safety_backup") else ""
            if reload_after:
                target_html = _bt().get_main_app_html() if result.get("configured") else _bt().get_setup_html()
                threading.Timer(0.1, _bt().window.load_html, args=(target_html,)).start()
            return {
                "success": True,
                "msg": f"Restored {len(result['restored'])} tracker config files to {result['config_dir']}.{safety}",
                "configured": result.get("configured", False),
            }
        except Exception as e:
            return {"success": False, "msg": f"Error restoring tracker config backup: {str(e)}"}
