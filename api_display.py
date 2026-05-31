import glob
import json
import os
import sys
import threading

from app_paths import get_base_path
from asset_helpers import (
    CALLING_CARD_DIR,
    EMBLEM_DIR,
    get_calling_card_src,
    get_emblem_variants,
    get_emblem_src,
    get_level_icon_src,
    get_prestige_icon_src,
    get_tier_icon_src,
    inline_theme_asset_urls,
)
from challenge_system import is_reserved_level_emblem
from game_data import ALWAYS_AVAILABLE_THEMES, LANGUAGE_OPTIONS, THEMES_DIR
from overlay_themes import OVERLAY_THEMES
from file_utils import load_json
from reward_assets import (
    ensure_reward_asset,
    get_cached_hosted_reward_assets,
    prepare_theme_css_for_display,
    rewrite_theme_urls_to_cdn,
    sync_theme_referenced_assets,
)

_bt = lambda: sys.modules["bo3tracker"]

CALLING_CARD_EXTENSIONS = [".mp4", ".webm", ".jpg", ".jpeg", ".png", ".webp", ".gif"]
EMBLEM_EXTENSIONS = [".mp4", ".webm", ".gif", ".jpg", ".jpeg", ".png", ".webp"]


def _asset_exists(folder, asset_name, extensions, allow_download=False):
    name = str(asset_name or "").strip()
    if not name or name == "default":
        return False
    folder_path = os.path.join(get_base_path(), folder)
    if any(os.path.exists(os.path.join(folder_path, f"{name}{ext}")) for ext in extensions):
        return True
    return bool(ensure_reward_asset(folder, name, extensions)) if allow_download else False


def _hosted_asset_known(folder, asset_name):
    name = str(asset_name or "").strip()
    if not name or name == "default":
        return False
    assets = get_cached_hosted_reward_assets().get(folder, [])
    return any(os.path.splitext(str(filename or ""))[0] == name for filename in assets)


def _asset_available_for_selector(folder, asset_name, extensions):
    return _asset_exists(folder, asset_name, extensions, allow_download=False) or _hosted_asset_known(folder, asset_name)


def _add_unique(items, value):
    name = str(value or "").strip()
    if name and name not in items:
        items.append(name)


def _reward_challenges():
    manager = _bt().challenge_manager
    challenges = []
    for attr in ("challenges", "map_challenges"):
        section = getattr(manager, attr, [])
        if isinstance(section, list):
            challenges.extend(c for c in section if isinstance(c, dict))
    return challenges


def _calling_card_exists(card_name):
    return _asset_available_for_selector(CALLING_CARD_DIR, card_name, CALLING_CARD_EXTENSIONS)


def _emblem_exists(emblem_name):
    return _asset_available_for_selector(EMBLEM_DIR, emblem_name, EMBLEM_EXTENSIONS)


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

        files = glob.glob(os.path.join(theme_path, "*.css"))
        all_themes = [os.path.basename(f).replace(".css", "") for f in files]

        unlocked = _bt().challenge_manager.get_unlocked_themes()
        candidates = set(unlocked) | set(ALWAYS_AVAILABLE_THEMES)
        active_theme = str(_bt().app_config.get('active_theme', '') or '').strip()
        if active_theme:
            candidates.add(active_theme)
        for t in candidates:
            if t not in all_themes and ensure_reward_asset(THEMES_DIR, t, [".css"]):
                all_themes.append(t)

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
        if not os.path.exists(path):
            downloaded = ensure_reward_asset(THEMES_DIR, theme_name, [".css"])
            if downloaded:
                path = downloaded
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw_css = f.read()
                    sync_theme_referenced_assets(raw_css)
                    raw_css = prepare_theme_css_for_display(raw_css)
                    css = inline_theme_asset_urls(raw_css, os.path.dirname(path), max_inline_bytes=None)
                    return rewrite_theme_urls_to_cdn(css, theme_name)
            except Exception:
                pass
        return ""

    def set_active_theme(self, theme_name):
        _bt().app_config['active_theme'] = theme_name
        _bt().save_app_config()
        _bt().push_overlay_theme()
        return True

    def get_compact_mode(self):
        return {"enabled": bool(_bt().app_config.get("compact_mode_enabled", False))}

    def set_compact_mode(self, enabled):
        _bt().app_config["compact_mode_enabled"] = bool(enabled)
        _bt().save_app_config()
        return {"success": True, "enabled": bool(_bt().app_config["compact_mode_enabled"])}

    # --- Calling Cards & Emblems ---
    def get_card_image(self, card_name):
        return get_calling_card_src(card_name)

    def get_emblem_image(self, emblem_name, variant="static"):
        return get_emblem_src(emblem_name, variant)

    def get_emblem_variants(self, emblem_name):
        return get_emblem_variants(emblem_name)

    def get_unlocked_calling_cards(self):
        unlocked_cards = ["default"]
        for reward_name in _bt().challenge_manager.get_unlocked_themes():
            card_name = str(reward_name or "").strip()
            if card_name and _calling_card_exists(card_name):
                _add_unique(unlocked_cards, card_name)
        for c in _reward_challenges():
            if c.get('completed') and c.get('reward_type') == 'calling_card':
                card_name = str(c.get('reward_val', '') or '').strip()
                _add_unique(unlocked_cards, card_name)
        active = str(_bt().app_config.get('active_card', '') or '').strip()
        if active and active != "default" and _calling_card_exists(active):
            _add_unique(unlocked_cards, active)
        return unlocked_cards

    def get_unlocked_emblems(self):
        live_path = _bt().app_config.get("live_path", "")
        if live_path and os.path.exists(live_path):
            _bt().challenge_manager.check_legend_emblem_unlocks_from_live_data(load_json(live_path))
        unlocked_emblems = ["default"]
        for reward_name in _bt().challenge_manager.get_unlocked_themes():
            emblem_name = str(reward_name or "").strip()
            if emblem_name and _emblem_exists(emblem_name):
                _add_unique(unlocked_emblems, emblem_name)
        for c in _reward_challenges():
            if c.get('completed') and c.get('reward_type') == 'emblem':
                emblem_name = str(c.get('reward_val', '') or '').strip()
                if not emblem_name:
                    continue
                if is_reserved_level_emblem(c.get('reward_type'), emblem_name):
                    continue
                _add_unique(unlocked_emblems, emblem_name)
        active = str(_bt().app_config.get('active_emblem', '') or '').strip()
        if active and active != "default" and _emblem_exists(active):
            _add_unique(unlocked_emblems, active)
        return unlocked_emblems

    def set_active_card(self, card_name):
        card_name = str(card_name or "default").strip() or "default"
        if card_name != "default" and card_name not in self.get_unlocked_calling_cards():
            card_name = "default"
        _bt().app_config['active_card'] = card_name
        _bt().save_app_config()
        return True

    def get_active_card(self):
        active = str(_bt().app_config.get('active_card', 'default') or 'default').strip() or "default"
        if active != "default" and active not in self.get_unlocked_calling_cards():
            _bt().app_config['active_card'] = "default"
            _bt().save_app_config()
            return "default"
        return active

    def set_active_emblem(self, emblem_name, variant="static"):
        emblem_name = str(emblem_name or "default").strip() or "default"
        if emblem_name != "default" and emblem_name not in self.get_unlocked_emblems():
            emblem_name = "default"
        variant = str(variant or "static").strip().lower()
        if variant not in ("static", "animated"):
            variant = "static"
        _bt().app_config['active_emblem'] = emblem_name
        _bt().app_config['active_emblem_variant'] = variant
        _bt().save_app_config()
        if (
            _bt().app_config.get("discord_presence_enabled", False)
            and str(_bt().app_config.get("discord_presence_image_source", "workshop") or "workshop").lower() == "emblem"
        ):
            live_path = _bt().app_config.get("live_path", "")
            if live_path and os.path.exists(live_path):
                try:
                    _bt().update_discord_presence_from_game(load_json(live_path) or {}, force=True)
                except Exception:
                    pass
        return True

    def get_active_emblem(self):
        active = str(_bt().app_config.get('active_emblem', 'default') or 'default').strip() or "default"
        if active != "default" and active not in self.get_unlocked_emblems():
            _bt().app_config['active_emblem'] = "default"
            _bt().save_app_config()
            return "default"
        return active

    def get_active_emblem_variant(self):
        variant = str(_bt().app_config.get('active_emblem_variant', 'static') or 'static').strip().lower()
        return variant if variant in ("static", "animated") else "static"

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
