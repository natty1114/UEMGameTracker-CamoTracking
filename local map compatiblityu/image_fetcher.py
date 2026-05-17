import os
import time
import threading
import requests
import re
import base64
import io
import json
from urllib.parse import urlparse, parse_qs

# --- Image Optimization Settings ---
MAX_IMAGE_WIDTH = 320          # Max width in pixels (height auto-scales)
JPEG_QUALITY = 60              # JPEG save quality 1-100 (lower = smaller)
CONFIG_FILE = os.path.join('config', 'uem_config.json')
DEFAULT_IMAGE_CACHE_ENABLED = True
DEFAULT_STORAGE_LIMIT_MB = 200
MAX_STORAGE_LIMIT_MB = 1024
STORAGE_LIMIT_BYTES = DEFAULT_STORAGE_LIMIT_MB * 1024 * 1024
MAX_PENDING_DOWNLOADS = 18     # Keep only the visible page plus a little breathing room
FAILED_RETRY_DELAY = 10 * 60   # Seconds before retrying a failed Steam image
RATE_LIMIT_BACKOFF = 5 * 60    # Seconds to pause new Steam calls after a 429


def get_image_cache_settings():
    settings = {
        'enabled': DEFAULT_IMAGE_CACHE_ENABLED,
        'limit_mb': DEFAULT_STORAGE_LIMIT_MB,
    }
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        settings['enabled'] = bool(config.get('image_cache_enabled', DEFAULT_IMAGE_CACHE_ENABLED))
        settings['limit_mb'] = int(config.get('image_cache_limit_mb', DEFAULT_STORAGE_LIMIT_MB))
    except Exception:
        pass

    settings['limit_mb'] = max(0, min(MAX_STORAGE_LIMIT_MB, settings['limit_mb']))
    settings['limit_bytes'] = settings['limit_mb'] * 1024 * 1024
    return settings


def _process_image_data(image_data, max_width=MAX_IMAGE_WIDTH, quality=JPEG_QUALITY):
    """Resize and compress image bytes to save disk space."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_data))
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        width, height = img.size
        if width > max_width:
            ratio = max_width / width
            new_w = int(max_width)
            new_h = int(height * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    except ImportError:
        return image_data
    except Exception as e:
        print(f"Image processing error: {e}")
        return image_data


def _ensure_storage_quota(image_folder, limit_bytes):
    """Remove oldest files until total size is under the limit."""
    if not os.path.exists(image_folder):
        return
    files = []
    for fname in os.listdir(image_folder):
        fpath = os.path.join(image_folder, fname)
        if os.path.isfile(fpath):
            try:
                files.append((fpath, os.path.getmtime(fpath), os.path.getsize(fpath)))
            except:
                pass
    total = sum(f[2] for f in files)
    if total <= limit_bytes:
        return
    files.sort(key=lambda f: f[1])  # oldest mtime first
    for fpath, _, fsize in files:
        if total <= limit_bytes:
            break
        try:
            os.remove(fpath)
            total -= fsize
            print(f"Storage quota: removed {os.path.basename(fpath)}")
        except:
            pass


class SteamImageFetcher:
    def __init__(self, callback=None, image_folder='steam_images', rate_limit=2.0, cache_enabled=None, storage_limit_bytes=None):
        self.callback = callback  # Simple function, NOT the window object
        self.image_folder = image_folder
        self.rate_limit = rate_limit
        image_settings = get_image_cache_settings()
        self.cache_enabled = image_settings['enabled'] if cache_enabled is None else cache_enabled
        self.storage_limit_bytes = image_settings['limit_bytes'] if storage_limit_bytes is None else storage_limit_bytes
        self.queue = [] 
        self.running = True
        self.lock = threading.Lock()
        self.wake_event = threading.Event()
        self.in_progress = set()
        self.failed_until = {}
        self.pause_until = 0
        self.session = requests.Session()
        
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)

    def set_callback(self, callback_func):
        """Sets the function to call when an image is ready."""
        self.callback = callback_func

    def cache_active(self):
        return self.cache_enabled and self.storage_limit_bytes > 0

    def queue_batch(self, items):
        """
        Queue the latest visible batch.
        items: list of {'id': '...', 'url': '...'}

        Cached images are returned immediately. Uncached images replace the
        pending queue so fast pagination does not build a huge Steam backlog.
        """
        new_items = []
        seen = set()
        now = time.time()

        for item in items:
            steam_id = item.get('id')
            url = item.get('url')
            if not steam_id or not url or steam_id in seen:
                continue
            seen.add(steam_id)

            local_path = os.path.join(self.image_folder, f"{steam_id}.jpg")

            # 1. If local file exists, trigger callback immediately
            if self.cache_active() and os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                os.utime(local_path, None)
                threading.Thread(target=self.notify_ui, args=(steam_id, local_path), daemon=True).start()
                continue

            if self.failed_until.get(steam_id, 0) > now:
                continue
            
            new_items.append((steam_id, url))

        with self.lock:
            pending = []
            queued_ids = set(self.in_progress)
            for steam_id, url in new_items:
                if steam_id in queued_ids:
                    continue
                pending.append((steam_id, url))
                queued_ids.add(steam_id)
                if len(pending) >= MAX_PENDING_DOWNLOADS:
                    break

            self.queue = pending
            pending_count = len(self.queue)

        if pending_count:
            print(f"Image queue refreshed. Pending visible downloads: {pending_count}")
            self.wake_event.set()

    def notify_ui(self, steam_id, image_path):
        """Reads image, converts to Base64, and calls the callback."""
        if not self.callback: return

        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            img_src = f"data:image/jpeg;base64,{encoded_string}"
            
            # Call the safe callback function provided by app.py
            self.callback(steam_id, img_src)
            
        except Exception as e:
            print(f"Error processing image {steam_id}: {e}")

    def notify_ui_bytes(self, steam_id, image_data):
        """Converts image bytes to Base64 and calls the callback without writing to disk."""
        if not self.callback:
            return
        try:
            encoded_string = base64.b64encode(image_data).decode('utf-8')
            img_src = f"data:image/jpeg;base64,{encoded_string}"
            self.callback(steam_id, img_src)
        except Exception as e:
            print(f"Error processing image bytes {steam_id}: {e}")

    def start(self):
        thread = threading.Thread(target=self._worker_loop, daemon=True)
        thread.start()

    def stop(self):
        self.running = False
        self.wake_event.set()
        with self.lock:
            self.queue = []

    def _worker_loop(self):
        print("Background Image Worker Started...")
        while self.running:
            item = None
            with self.lock:
                if self.queue:
                    item = self.queue.pop(0)
                    self.in_progress.add(item[0])
            
            if item:
                steam_id, url = item
                try:
                    pause_for = self.pause_until - time.time()
                    if pause_for > 0:
                        print(f"Steam image worker paused for {int(pause_for)}s after rate limit.")
                        time.sleep(min(pause_for, RATE_LIMIT_BACKOFF))
                    self._download_and_save(steam_id, url)
                finally:
                    with self.lock:
                        self.in_progress.discard(steam_id)
                time.sleep(self.rate_limit)
            else:
                self.wake_event.wait(0.5)
                self.wake_event.clear()

    def _download_and_save(self, steam_id, url):
        print(f"Downloading: {steam_id}")
        local_path = os.path.join(self.image_folder, f"{steam_id}.jpg")

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 429:
                self.pause_until = time.time() + RATE_LIMIT_BACKOFF
                self.failed_until[steam_id] = time.time() + FAILED_RETRY_DELAY
                print(f"Steam rate limited image lookup for {steam_id}; pausing image downloads.")
                return
            
            if response.status_code == 200:
                # Try to find og:image
                match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
                if match:
                    img_url = match.group(1)
                    img_response = self.session.get(img_url, headers=headers, timeout=10)
                    if img_response.status_code == 429:
                        self.pause_until = time.time() + RATE_LIMIT_BACKOFF
                        self.failed_until[steam_id] = time.time() + FAILED_RETRY_DELAY
                        print(f"Steam rate limited image download for {steam_id}; pausing image downloads.")
                        return
                    img_response.raise_for_status()
                    img_data = img_response.content
                    # Resize and compress to save disk space
                    img_data = _process_image_data(img_data)
                    if self.cache_active():
                        with open(local_path, 'wb') as f:
                            f.write(img_data)
                        # Enforce storage quota (remove oldest if over limit)
                        _ensure_storage_quota(self.image_folder, self.storage_limit_bytes)
                        self.notify_ui(steam_id, local_path)
                    else:
                        self.notify_ui_bytes(steam_id, img_data)
                else:
                    print(f"No image meta tag found for {steam_id}")
                    self.failed_until[steam_id] = time.time() + FAILED_RETRY_DELAY
            else:
                print(f"Steam image lookup failed for {steam_id}: HTTP {response.status_code}")
                self.failed_until[steam_id] = time.time() + FAILED_RETRY_DELAY
        except Exception as e:
            print(f"Error downloading {steam_id}: {e}")
            self.failed_until[steam_id] = time.time() + FAILED_RETRY_DELAY
