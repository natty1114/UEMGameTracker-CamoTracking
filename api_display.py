import glob
import json
import os
import sys
import threading

from app_paths import get_base_path
from asset_helpers import (
    get_calling_card_src,
    get_emblem_src,
    get_level_icon_src,
    get_prestige_icon_src,
    get_tier_icon_src,
    inline_theme_asset_urls,
)
from game_data import ALWAYS_AVAILABLE_THEMES, LANGUAGE_OPTIONS, THEMES_DIR
from overlay_themes import OVERLAY_THEMES
from file_utils import load_json

_bt = lambda: sys.modules["bo3tracker"]


class DisplayAPI:
    # --- Localization ---
    def get_language_options(self):
        return LANGUAGE_OPTIONS

    def get_active_language(self):
        return _bt().app_config.get("language", "en")

    def set_active_language(self, language_code):
        valid_codes = {item["code"] for item in LANGUAGE_OPTIONS}
        code = str(language_code or "en").strip()
        if code not in valid_codes:
            code = "en"
        _bt().app_config["language"] = code
        _bt().save_app_config()
        return {"success": True, "language": code}

    def get_locale_strings(self, language_code):
        code = str(language_code or "en").strip()
        if code == "en":
            return {}
        valid_codes = {item["code"] for item in LANGUAGE_OPTIONS}
        if code not in valid_codes:
            return {}
        path = os.path.join(get_base_path(), "locales", f"{code}.json")
        data = load_json(path)
        return data if isinstance(data, dict) else {}

    # --- Themes ---
    def set_theme(self, theme_name):
        _bt().app_config['active_theme'] = theme_name
        _bt().save_app_config()
        _bt().push_overlay_theme()
        return True

    def get_active_theme(self):
        return _bt().app_config.get('active_theme', 'default')

    def get_available_themes(self):
        theme_path = os.path.join(get_base_path(), THEMES_DIR)
        if not os.path.exists(theme_path):
            os.makedirs(theme_path)
            return []

        files = glob.glob(os.path.join(theme_path, "*.css"))
        all_themes = [os.path.basename(f).replace(".css", "") for f in files]

        unlocked = _bt().challenge_manager.get_unlocked_themes()

        valid_themes = []
        if "default" not in unlocked:
            unlocked.append("default")

        for t in all_themes:
            if t in ALWAYS_AVAILABLE_THEMES or t in unlocked or t == "default":
                valid_themes.append(t)

        return valid_themes

    def get_theme_content(self, theme_name):
        if theme_name == "default":
            return ""

        path = os.path.join(get_base_path(), THEMES_DIR, f"{theme_name}.css")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return inline_theme_asset_urls(f.read(), os.path.dirname(path), max_inline_bytes=None)
            except Exception:
                pass
        return ""

    def set_active_theme(self, theme_name):
        _bt().app_config['active_theme'] = theme_name
        _bt().save_app_config()
        _bt().push_overlay_theme()
        return True

    # --- Calling Cards & Emblems ---
    def get_card_image(self, card_name):
        return get_calling_card_src(card_name)

    def get_emblem_image(self, emblem_name):
        return get_emblem_src(emblem_name)

    def get_unlocked_calling_cards(self):
        challenges = _bt().challenge_manager.get_frontend_data()
        unlocked_cards = ["default"]
        for c in challenges:
            if c['completed'] and c['reward_type'] == 'calling_card':
                card_name = c['reward_val']
                if card_name not in unlocked_cards:
                    unlocked_cards.append(card_name)
        return unlocked_cards

    def get_unlocked_emblems(self):
        challenges = _bt().challenge_manager.get_frontend_data()
        unlocked_emblems = ["default"]
        for c in challenges:
            if c['completed'] and c['reward_type'] == 'emblem':
                emblem_name = c['reward_val']
                if emblem_name not in unlocked_emblems:
                    unlocked_emblems.append(emblem_name)
        for reward_name in _bt().challenge_manager.get_unlocked_themes():
            if reward_name not in unlocked_emblems and get_emblem_src(reward_name):
                unlocked_emblems.append(reward_name)
        return unlocked_emblems

    def set_active_card(self, card_name):
        _bt().app_config['active_card'] = card_name
        _bt().save_app_config()
        return True

    def get_active_card(self):
        return _bt().app_config.get('active_card', 'default')

    def set_active_emblem(self, emblem_name):
        _bt().app_config['active_emblem'] = emblem_name
        _bt().save_app_config()
        return True

    def get_active_emblem(self):
        return _bt().app_config.get('active_emblem', 'default')

    # --- Workshop Images ---
    def get_workshop_image(self, steam_link_id):
        if not _bt().app_config.get('workshop_images_enabled', True):
            return None
        from workshop_images import get_workshop_image
        return get_workshop_image(steam_link_id)

    def toggle_workshop_images(self, enabled):
        _bt().app_config['workshop_images_enabled'] = bool(enabled)
        _bt().save_app_config()
        return True
