"""Asset loading helpers for BO3 Tracker."""

import base64
import mimetypes
import os
import re
from pathlib import Path

from app_paths import get_base_path


ICONS_DIR_NAME = "perk icons"
RANK_ICONS_DIR_NAME = "rank icons"
CAMO_IMG_DIR = "camoimages"
CALLING_CARD_DIR = "callingcards"
EMBLEM_DIR = "emblems"
AAT_ICON_DIR = "aat icons"


def load_css(filename):
    try:
        path = os.path.join(get_base_path(), filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return inline_theme_asset_urls(f.read(), os.path.dirname(path))
    except Exception:
        pass
    return "/* CSS FILE NOT FOUND */"


def inline_theme_asset_urls(css_content, theme_dir, max_inline_bytes=500_000):
    def replace_url(match):
        quote = match.group("quote") or ""
        asset_url = match.group("url").strip()
        lowered = asset_url.lower()
        if lowered.startswith(("data:", "http://", "https://", "file:", "#")):
            return match.group(0)

        asset_path = os.path.normpath(os.path.join(theme_dir, asset_url.replace("/", os.sep)))
        try:
            if not asset_path.startswith(os.path.normpath(theme_dir)) or not os.path.exists(asset_path):
                return match.group(0)
            if max_inline_bytes is None or os.path.getsize(asset_path) <= max_inline_bytes:
                mime = mimetypes.guess_type(asset_path)[0] or "application/octet-stream"
                with open(asset_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("ascii")
                return f"url({quote}data:{mime};base64,{encoded}{quote})"
            return f"url({quote}{Path(asset_path).as_uri()}{quote})"
        except Exception:
            return match.group(0)

    return re.sub(r"url\((?P<quote>['\"]?)(?P<url>[^'\")]+)(?P=quote)\)", replace_url, css_content)


def sanitize_filename(name):
    return str(name).replace(":", "_").replace("|", "_").replace("/", "_").replace("\\", "_")


def get_base64_icon(perk_key):
    icons_folder = os.path.join(get_base_path(), ICONS_DIR_NAME)
    for ext in [".webp", ".png"]:
        target = os.path.join(icons_folder, perk_key + ext)
        if os.path.exists(target):
            try:
                with open(target, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    mime = "image/webp" if ext == ".webp" else "image/png"
                    return "data:" + mime + ";base64," + b64
            except Exception:
                pass
    return None


def get_aat_icon_src(aat_key):
    safe_key = sanitize_filename(aat_key).strip()
    if not safe_key:
        return None
    icons_folder = os.path.join(get_base_path(), AAT_ICON_DIR)
    for ext in [".webp", ".png"]:
        target = os.path.join(icons_folder, safe_key + ext)
        if os.path.exists(target):
            try:
                with open(target, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    mime = "image/webp" if ext == ".webp" else "image/png"
                    return "data:" + mime + ";base64," + b64
            except Exception:
                pass
    return None


def get_rank_icon_base64(filename):
    target = os.path.join(get_base_path(), RANK_ICONS_DIR_NAME, filename)
    if os.path.exists(target):
        try:
            with open(target, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{b64}"
        except Exception:
            pass
    return None


def get_tier_icon_src(tier_type, tier_value):
    safe_val = int(tier_value)
    if safe_val <= 0:
        return None
    img_name = f"ui_icon_rank_tier_{tier_type}_{safe_val}_large.png"
    return get_rank_icon_base64(img_name)


def get_prestige_icon_src(prestige):
    safe_prestige = min(max(int(prestige), 0), 20)
    if safe_prestige == 0:
        return None
    img_name = f"ui_icon_ranks_prestige_{safe_prestige}_large.png"
    return get_rank_icon_base64(img_name)


def get_level_icon_src(level):
    lvl = int(level)
    if lvl < 100:
        safe_level = min(max(lvl, 1), 90)
        img_name = f"ui_icon_rank_mp_level{safe_level}_large.png"
    else:
        rank_tier = (lvl // 100) * 100
        img_name = f"ui_icon_rank_mp_level{rank_tier}_large.png"

    return get_rank_icon_base64(img_name)


def get_camo_image_src(index):
    img_name = f"camo_{index}.png"
    target = os.path.join(get_base_path(), CAMO_IMG_DIR, img_name)
    if os.path.exists(target):
        try:
            with open(target, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{b64}"
        except Exception:
            pass
    return None


def get_calling_card_src(card_name):
    if not card_name or card_name == "default":
        return None
    for ext in [".mp4", ".webm", ".jpg", ".png", ".webp"]:
        img_name = f"{card_name}{ext}"
        target = os.path.join(get_base_path(), CALLING_CARD_DIR, img_name)
        if os.path.exists(target):
            try:
                with open(target, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    mime = ""
                    if ext == ".mp4":
                        mime = "video/mp4"
                    elif ext == ".webm":
                        mime = "video/webm"
                    elif ext == ".jpg":
                        mime = "image/jpeg"
                    else:
                        mime = f"image/{ext[1:]}"

                    return f"data:{mime};base64,{b64}"
            except Exception:
                pass
    return None


def get_emblem_src(emblem_name):
    if not emblem_name or emblem_name == "default":
        return None
    for ext in [".mp4", ".webm", ".jpg", ".jpeg", ".png", ".webp"]:
        img_name = f"{emblem_name}{ext}"
        target = os.path.join(get_base_path(), EMBLEM_DIR, img_name)
        if os.path.exists(target):
            try:
                with open(target, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    mime = mimetypes.guess_type(target)[0] or "application/octet-stream"
                    return f"data:{mime};base64,{b64}"
            except Exception:
                pass
    return None
