import requests
import json
import os
import time
import sys
from datetime import datetime

# --- CONFIGURATION ---
URL = "https://script.googleusercontent.com/macros/echo?user_content_key=AehSKLhOBOV5kCdZll4DLVWs-iNZIoxT6hQ957dGWshz-snfSJCG8uK0CZGokTk3BFjXyONnPbIo3LdfburEpX-sqeIx5k1E-hnQ7Z9WwQn5nHleavVKowxkdMQgSIMqRh6a-CJ8fUWO-Ds7PlI7qgEUgIsIvvS-ePSrnNJls2GD1Dqm_Nwo-KIqSYdhk4S3X_xcQg-cdunrBwX4G80JiJc87s0zgFdv1n85wuyDaG2MDVtcWl-gg9KZjhLdC9yU9yDBe8HV3nWewodnDrX_T2pHXJKjKLgVPZOkFWIQQtnh&lib=M4T5dabjBZQlsaSQw7XutbqNHYQyjQeWH"
FILE_NAME = "uem_cache.json"

# How often to actually download from the internet (in seconds)
# 1800 seconds = 30 minutes
DOWNLOAD_COOLDOWN = 1800 

def get_local_data():
    """Reads the current local JSON file."""
    if not os.path.exists(FILE_NAME):
        return None
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def update_database():
    # 1. Check if we should download (Rate Limiting)
    if os.path.exists(FILE_NAME):
        last_modified = os.path.getmtime(FILE_NAME)
        time_since_update = time.time() - last_modified
        
        if time_since_update < DOWNLOAD_COOLDOWN:
            minutes_left = int((DOWNLOAD_COOLDOWN - time_since_update) / 60)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Cache is fresh. Next check in ~{minutes_left} mins.")
            return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking for updates...")

    # 2. Download Data
    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
        new_data = response.json()
    except Exception as e:
        print(f"Error downloading data: {e}")
        return

    # 3. Compare with Local
    current_data = get_local_data()

    # Sort keys to ensure accurate comparison
    if current_data == new_data:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No changes found on server.")
        # Touch the file to update the timestamp so we don't check again for 30 mins
        os.utime(FILE_NAME, None)
    else:
        # 4. Save if different
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ➤ UPDATING DATABASE with new data!")
        with open(FILE_NAME, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=4)

def main():
    print("--- UEM Database Auto-Updater Started ---")
    print(f"Target: {FILE_NAME}")
    print(f"Update Interval: Every {int(DOWNLOAD_COOLDOWN/60)} minutes")
    print("-----------------------------------------")

    while True:
        update_database()
        # Sleep for a bit before checking loop again to save CPU
        # We check often (every minute) just to see if the cooldown expired
        time.sleep(60) 

if __name__ == "__main__":
    main()