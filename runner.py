import json
import importlib.util
import os
import shutil
import zipfile

# Name of your main script
MAIN_SCRIPT = "bo3tracker.py"
# Name of the resulting executable
EXE_NAME = "BO3Tracker"
UPDATER_SCRIPT = "updater.py"
UPDATER_EXE_NAME = "BO3Updater"
MAP_COMPAT_DIR = "local map compatiblityu"
MAP_COMPAT_BUILD_SCRIPT = "build_map_compat.py"

FORBIDDEN_RELEASE_NAMES = {
    "config" + ".php",
    "global_stats_config.json",
    "global_stats_state.json",
    "config.json",
    "register.php",
    "migration_add_tokens_table.sql",
}

FORBIDDEN_RELEASE_TEXT = [
    "DB" + "_PASS",
    "uemmmiao" + "_statsadmin",
    "GLOBAL_STATS_INGEST_TOKEN =",
    "contributor_tokens",
    "register.php",
]


def fail(message):
    print(f"Error: {message}")
    raise SystemExit(1)


def assert_clean_release_folder(release_dir):
    for root, _, files in os.walk(release_dir):
        for filename in files:
            if filename in FORBIDDEN_RELEASE_NAMES:
                fail(f"Forbidden runtime/server file in release: {os.path.join(root, filename)}")


def assert_source_script_is_safe(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        text = handle.read()

    for marker in FORBIDDEN_RELEASE_TEXT:
        if marker in text:
            fail(f"Forbidden server/private marker found in release script {path}: {marker}")


def get_app_version():
    with open("app_version.json", "r", encoding="utf-8") as handle:
        data = json.load(handle)

    version = str(data.get("version") or "").strip()
    if not version:
        fail("version not found in app_version.json")
    return version


def create_release_zip(release_dir, version):
    zip_name = f"{EXE_NAME}-{version}.zip"
    if os.path.exists(zip_name):
        os.remove(zip_name)

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(release_dir):
            for filename in files:
                full_path = os.path.join(root, filename)
                arcname = os.path.relpath(full_path, release_dir)
                archive.write(full_path, arcname)

    print(f"Release zip created: {zip_name}")
    return zip_name


def build_map_compat_release(release_dir):
    build_script = os.path.join(MAP_COMPAT_DIR, MAP_COMPAT_BUILD_SCRIPT)
    if not os.path.exists(build_script):
        print(f"Warning: Map compatibility build script not found: {build_script}")
        return

    spec = importlib.util.spec_from_file_location("build_map_compat", build_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    output_dir = os.path.join(release_dir, MAP_COMPAT_DIR)
    module.build(output_dir=output_dir, include_credentials=False)


def build():
    import PyInstaller.__main__

    print("--- STARTING COMPILATION ---")

    if not os.path.exists(MAIN_SCRIPT):
        fail(f"Main script not found: {MAIN_SCRIPT}")
    if not os.path.exists(UPDATER_SCRIPT):
        fail(f"Updater script not found: {UPDATER_SCRIPT}")
    app_version = get_app_version()
    print(f"Release version: {app_version}")
    
    # PyInstaller arguments
    args = [
        MAIN_SCRIPT,
        f'--name={EXE_NAME}',
        '--onefile',        # Create a single .exe file
        '--noconsole',      # Hide the black command window (GUI mode)
        '--clean',          # Clean cache before building
        '--noupx',          # Disable UPX to reduce AV false positives
        '--version-file=version_info_bo3tracker.txt',
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)

    updater_args = [
        UPDATER_SCRIPT,
        f'--name={UPDATER_EXE_NAME}',
        '--onefile',
        '--noconsole',
        '--clean',
        '--noupx',
        '--version-file=version_info_updater.txt',
    ]
    PyInstaller.__main__.run(updater_args)
    
    print("--- COMPILATION FINISHED ---")
    print("--- MOVING FILES ---")

    # Define paths
    dist_folder = "dist"
    exe_path = os.path.join(dist_folder, f"{EXE_NAME}.exe")
    updater_exe_path = os.path.join(dist_folder, f"{UPDATER_EXE_NAME}.exe")
    
    # Check if build was successful
    if not os.path.exists(exe_path):
        fail("Build failed. Executable not found.")
    if not os.path.exists(updater_exe_path):
        fail("Build failed. Updater executable not found.")

    # Create a 'Release' folder to put everything in. If the current release is
    # running and Windows locks it, fall back to a versioned staging folder.
    release_dir = "Release_Build"
    if os.path.exists(release_dir):
        try:
            shutil.rmtree(release_dir)
        except PermissionError:
            release_dir = f"Release_Build_{app_version}"
            print(f"Warning: Release_Build is locked. Using {release_dir} instead.")
            if os.path.exists(release_dir):
                shutil.rmtree(release_dir)
    os.makedirs(release_dir)

    # Move the EXE to the release folder
    shutil.move(exe_path, os.path.join(release_dir, f"{EXE_NAME}.exe"))
    shutil.move(updater_exe_path, os.path.join(release_dir, f"{UPDATER_EXE_NAME}.exe"))

    print("--- BUILDING MAP COMPATIBILITY APP ---")
    build_map_compat_release(release_dir)
    
    print(f"Executable moved to: {release_dir}")
    print("--- COPYING ASSETS ---")
    
    # List of folders/files your app needs to run
    assets_to_copy = [
        "perk icons",
        "camoimages",
        "callingcards",
        "emblems",
        "themes",
        "locales",
        "style.css",
        "setup.css",
        "app_version.json",
        "custom_camos.json",
        "rank icons",
        "aat icons",
        "xp_requirements.csv",
        "chart.js",
        "default_tactical_background.jpg",
        "default_tactical_background.png",
        "themes/grafftiimage.png",
    ]

    for asset in assets_to_copy:
        if os.path.exists(asset):
            target = os.path.join(release_dir, asset)
            if os.path.isdir(asset):
                shutil.copytree(asset, target)
                print(f"Copied folder: {asset}")
            else:
                shutil.copy(asset, target)
                print(f"Copied file: {asset}")
        else:
            print(f"Warning: Asset not found: {asset}")

    print("--- COPYING SAFE CONFIG SEEDS ---")
    config_seed_dir = os.path.join(release_dir, "config")
    os.makedirs(config_seed_dir, exist_ok=True)
    config_seeds_to_copy = [
        "config/map_challenges.json",
        "config/map_weapons.json",
    ]
    for config_seed in config_seeds_to_copy:
        if os.path.exists(config_seed):
            target = os.path.join(config_seed_dir, os.path.basename(config_seed))
            shutil.copy(config_seed, target)
            print(f"Copied config seed: {config_seed}")
        else:
            print(f"Warning: Config seed not found: {config_seed}")

    # --- SPECIFIC SCRIPTS COPIED TO SOURCE FOLDER ---
    print("--- COPYING SOURCE SCRIPTS ---")
    scripts_dir = os.path.join(release_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    
    # Explicitly define ONLY the required scripts
    source_scripts = [
        "api_display.py",
        "api_data.py",
        "api_network.py",
        "api_system.py",
        "bo3tracker.py",
        "asset_helpers.py",
        "app_metadata.py",
        "app_paths.py",
        "best_matches.py",
        "camo_processor.py",
        "custom_camos_sync.py",
        "discord_presence.py",
        "ui_main.py",
        "ui_views.py",
        "game_data.py",
        "overlay_themes.py",
        "file_utils.py",
        "player_stats_backup.py",
        "remote_management_client.py",
        "version_utils.py",
        "damage_memory.py",
        "stats_processor.py",
        "match_xp.py",
        "xp_overflow_recovery.py",
        "challenge_system.py",
        "weapon_categories.py",
        "sync_map_challenges.py",
        "map_weapons.py",
        "sync_map_weapons.py",
        "xpm_grapher.py",
        "workshop_images.py",
        "global_stats_client.py",
        "updater.py",
        "DEV_LOG.md",
        "CHANGELOG_4.0.0.md",
        "CHANGELOG_4.0.1.md",
        "CHANGELOG_4.2.md",
        "CHANGELOG_4.4.0.md",
        "CHANGELOG_4.5.0.md",
        "CHANGELOG_4.6.0.md"
    ]

    for source_file in source_scripts:
        if os.path.exists(source_file):
            if source_file.endswith(".py"):
                assert_source_script_is_safe(source_file)
            target_file = os.path.join(scripts_dir, source_file)
            shutil.copy(source_file, target_file)
            print(f"Copied source file: {source_file}")
        else:
            print(f"Warning: Source file not found: {source_file}")

    assert_clean_release_folder(release_dir)
    create_release_zip(release_dir, app_version)
    print("--- BUILD PROCESS COMPLETE ---")

if __name__ == "__main__":
    build()
