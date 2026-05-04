"""
workshop_images.py - Steam Workshop image scraper and cache manager for BO3 Tracker.

Fetches map preview images from Steam Workshop pages by scraping HTML,
downloads them at 400px resolution, and manages a local disk cache
with a 250MB size cap and 24-hour access-based eviction.
"""

import os
import re
import time
import base64
import threading
from pathlib import Path

try:
    import urllib.request
    import urllib.parse
except ImportError:
    urllib = None

try:
    import requests
except ImportError:
    requests = None

CACHE_DIR_NAME = "workshop_image_cache"
MAX_CACHE_SIZE_MB = 250
MAX_CACHE_SIZE_BYTES = MAX_CACHE_SIZE_MB * 1024 * 1024
ACCESS_GRACE_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT = 8

_lock = threading.Lock()


def _get_base_path():
    """Return the directory where this module's script file lives."""
    return os.path.dirname(os.path.abspath(__file__))


def _get_cache_dir():
    """Ensure the cache directory exists and return its path."""
    cache_path = os.path.join(_get_base_path(), CACHE_DIR_NAME)
    os.makedirs(cache_path, exist_ok=True)
    return cache_path


def _scrape_image_url(steam_link_id):
    """
    Scrape the workshop page and return the main preview image URL at 400px.

    Returns the image URL string or None if extraction failed.
    """
    page_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={steam_link_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    html = None

    if requests is not None:
        try:
            resp = requests.get(page_url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                html = resp.text
        except Exception:
            pass

    if html is None and urllib is not None:
        try:
            req = urllib.request.Request(page_url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            pass

    if html is None:
        return None

    match = re.search(
        r'<img\s+id="previewImageMain"[^>]*\bsrc="([^"]+)"',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        match = re.search(
            r'<img[^>]*\bclass="workshopItemPreviewImageMain"[^>]*\bsrc="([^"]+)"',
            html,
            re.IGNORECASE | re.DOTALL,
        )

    if not match:
        return None

    img_url = match.group(1).replace("&amp;", "&")
    img_url = re.sub(
        r"[?&]imw=\d+",
        "?imw=200",
        img_url,
    )
    img_url = re.sub(
        r"[?&]imh=\d+",
        "&imh=200",
        img_url,
    )
    if "letterbox=" in img_url:
        img_url = re.sub(r"letterbox=[^&]*", "letterbox=false", img_url)
    if "imcolor=" in img_url:
        img_url = re.sub(r"imcolor=[^&]*", "imcolor=%23000000", img_url)

    return img_url


def _download_image(img_url, save_path):
    """
    Download an image from a URL and save it to save_path.

    Returns True on success, False on failure.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    if requests is not None:
        try:
            resp = requests.get(img_url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return True
        except Exception:
            pass

    if urllib is not None:
        try:
            req = urllib.request.Request(img_url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = resp.read()
                with open(save_path, "wb") as f:
                    f.write(data)
                return True
        except Exception:
            pass

    return False


def _get_cache_size():
    """Return total size of all files in the cache directory in bytes."""
    cache_dir = _get_cache_dir()
    total = 0
    for entry in os.scandir(cache_dir):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def _cleanup_cache():
    """
    Evict cached images that have not been accessed in 24 hours when
    the cache exceeds 250MB.  Oldest files are removed first.
    """
    cache_dir = _get_cache_dir()
    current_size = _get_cache_size()

    if current_size <= MAX_CACHE_SIZE_BYTES:
        return

    now = time.time()
    files = []
    for entry in os.scandir(cache_dir):
        if entry.is_file():
            st = entry.stat()
            files.append({
                "path": entry.path,
                "size": st.st_size,
                "atime": st.st_atime,
                "age": now - st.st_atime,
            })

    files.sort(key=lambda f: f["atime"])

    for info in files:
        if current_size <= MAX_CACHE_SIZE_BYTES:
            break
        if info["age"] >= ACCESS_GRACE_SECONDS:
            try:
                os.remove(info["path"])
                current_size -= info["size"]
            except OSError:
                pass


def get_workshop_image(steam_link_id):
    """
    Return a base64 data URL for the workshop image of the given Steam
    workshop ID.

    Workflow:
    1. Check if the image is already cached locally.
    2. If cached, update its access time and return the base64 string.
    3. If not cached, scrape the workshop page for the preview image URL.
    4. Download the image, save to cache, run cleanup, and return the
       base64 string.

    Returns None if the image could not be obtained.
    """
    if not steam_link_id or str(steam_link_id).strip() == "0":
        return None

    cache_dir = _get_cache_dir()
    cache_file = os.path.join(cache_dir, f"{steam_link_id}.jpg")

    with _lock:
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    data = f.read()
                os.utime(cache_file, None)
                _cleanup_cache()
                return f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"
            except Exception:
                pass

        img_url = _scrape_image_url(str(steam_link_id))
        if not img_url:
            return None

        if _download_image(img_url, cache_file):
            try:
                _cleanup_cache()
                with open(cache_file, "rb") as f:
                    data = f.read()
                return f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"
            except Exception:
                pass

    return None
