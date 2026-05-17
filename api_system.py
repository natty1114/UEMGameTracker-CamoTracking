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
    # --- Config ---
    def save_config(self, live, hist):
        _bt().app_config['live_path'] = live
        _bt().app_config['history_path'] = hist
        _bt().save_app_config()
        t = threading.Timer(0.1, _bt().window.load_html, args=(_bt().get_main_app_html(),))
        t.start()
        return True

    def reset_config(self):
        _bt().app_config = {}
        save_json(get_runtime_path(CONFIG_FILE), {})
        return True

    def launch_setup(self):
        t = threading.Timer(0.1, _bt().window.load_html, args=(_bt().get_setup_html(),))
        t.start()
        return True

    def launch_dashboard(self):
        return True

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
        return _bt().launch_map_compat_window()

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
