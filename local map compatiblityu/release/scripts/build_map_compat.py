import os
import shutil
import sys


APP_NAME = "UEMMapCompatibility"
MAIN_SCRIPT = "app.py"

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(LOCAL_DIR)

RUNTIME_FILES = [
    "uem_cache.json",
    "CHANGELOG.md",
    "DEVLOG.md",
]

RUNTIME_DIRS = [
    "themesmap",
    "steam_images",
]

SOURCE_FILES = [
    "app.py",
    "help_page.py",
    "image_fetcher.py",
    "settings_page.py",
    "sheet_db.py",
    "steam_scraper.py",
    "update_db.py",
    "build_map_compat.py",
    "apps_script_submission_endpoint.gs",
    "UEMMapCompatibility.spec",
]

SENSITIVE_CONFIG_NAMES = {
    "google_credentials.json",
}

SENSITIVE_TEXT_MARKERS = [
    '"private_key"',
    "-----BEGIN PRIVATE KEY-----",
    "client_email",
]


def fail(message):
    print(f"Error: {message}")
    raise SystemExit(1)


def _remove_existing(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def _copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def _looks_sensitive_config(path):
    if os.path.basename(path) in SENSITIVE_CONFIG_NAMES:
        return True
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
    except Exception:
        return False
    return any(marker in text for marker in SENSITIVE_TEXT_MARKERS)


def _copy_config(output_dir, include_credentials=False):
    src_config = os.path.join(LOCAL_DIR, "config")
    if not os.path.isdir(src_config):
        return

    dst_config = os.path.join(output_dir, "config")
    os.makedirs(dst_config, exist_ok=True)
    for name in os.listdir(src_config):
        src = os.path.join(src_config, name)
        dst = os.path.join(dst_config, name)
        if os.path.isdir(src):
            continue
        if not include_credentials and _looks_sensitive_config(src):
            print(f"Skipped sensitive config: config\\{name}")
            continue
        _copy_file(src, dst)


def copy_runtime_assets(output_dir, include_credentials=False):
    for filename in RUNTIME_FILES:
        src = os.path.join(LOCAL_DIR, filename)
        if os.path.exists(src):
            _copy_file(src, os.path.join(output_dir, filename))
        else:
            print(f"Warning: runtime file not found: {filename}")

    for dirname in RUNTIME_DIRS:
        src = os.path.join(LOCAL_DIR, dirname)
        dst = os.path.join(output_dir, dirname)
        if os.path.isdir(src):
            _remove_existing(dst)
            shutil.copytree(src, dst)
        else:
            print(f"Warning: runtime folder not found: {dirname}")

    _copy_config(output_dir, include_credentials=include_credentials)


def copy_source_snapshot(output_dir):
    scripts_dir = os.path.join(output_dir, "scripts")
    _remove_existing(scripts_dir)
    os.makedirs(scripts_dir, exist_ok=True)
    for filename in SOURCE_FILES:
        src = os.path.join(LOCAL_DIR, filename)
        if os.path.exists(src):
            _copy_file(src, os.path.join(scripts_dir, filename))
        else:
            print(f"Warning: source file not found: {filename}")


def build(output_dir=None, include_credentials=False):
    try:
        import PyInstaller.__main__
    except ImportError:
        fail("PyInstaller is not installed.")

    main_script = os.path.join(LOCAL_DIR, MAIN_SCRIPT)
    if not os.path.exists(main_script):
        fail(f"Map compatibility script not found: {MAIN_SCRIPT}")

    dist_dir = os.path.join(LOCAL_DIR, "dist")
    build_dir = os.path.join(LOCAL_DIR, "build")
    spec_path = os.path.join(LOCAL_DIR, "UEMMapCompatibility.spec")

    args = [
        spec_path if os.path.exists(spec_path) else main_script,
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        "--noconfirm",
        "--clean",
    ]
    if not os.path.exists(spec_path):
        args.extend([
            f"--name={APP_NAME}",
            "--onefile",
            "--noconsole",
            "--hidden-import=help_page",
            "--hidden-import=settings_page",
        ])

    PyInstaller.__main__.run(args)

    built_exe = os.path.join(dist_dir, f"{APP_NAME}.exe")
    if not os.path.exists(built_exe):
        fail(f"Build failed. Executable not found: {built_exe}")

    if output_dir is None:
        output_dir = os.path.join(LOCAL_DIR, "release")

    _remove_existing(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    _copy_file(built_exe, os.path.join(output_dir, f"{APP_NAME}.exe"))
    copy_runtime_assets(output_dir, include_credentials=include_credentials)
    copy_source_snapshot(output_dir)

    print(f"Map compatibility release created: {output_dir}")
    if not include_credentials:
        print("Google credentials were not packaged. Add config\\google_credentials.json manually if report submissions must work in this build.")
    return output_dir


if __name__ == "__main__":
    include_credentials = "--include-credentials" in sys.argv
    build(include_credentials=include_credentials)
