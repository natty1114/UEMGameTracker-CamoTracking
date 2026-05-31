import ast
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parent


PYTHON_FILES = [
    "api_data.py",
    "api_display.py",
    "api_network.py",
    "api_system.py",
    "app_metadata.py",
    "app_paths.py",
    "asset_helpers.py",
    "best_matches.py",
    "bo3tracker_launcher.py",
    "bo3tracker.py",
    "camo_processor.py",
    "challenge_system.py",
    "currentgame_sync.py",
    "weapon_categories.py",
    "sync_map_challenges.py",
    "damage_memory.py",
    "discord_presence.py",
    "file_utils.py",
    "game_data.py",
    "global_stats_client.py",
    "match_xp.py",
    "overlay_themes.py",
    "player_stats_backup.py",
    "remote_management_client.py",
    "runner.py",
    "stats_processor.py",
    "ui_main.py",
    "ui_views.py",
    "updater.py",
    "version_utils.py",
    "workshop_images.py",
    "xp_overflow_recovery.py",
    "xpm_grapher.py",
]

DEV_TOOL_PYTHON_FILES = [
    "dev_tools/admin_gui.py",
    "dev_tools/modules/__init__.py",
    "dev_tools/modules/challenge_catalog.py",
    "dev_tools/modules/challenge_difficulty.py",
    "dev_tools/modules/challenge_manifest.py",
    "dev_tools/modules/ftp_uploader.py",
    "dev_tools/modules/global_stats_control.py",
    "dev_tools/modules/local_weekly_templates.py",
    "dev_tools/modules/remote_management_manifest.py",
    "dev_tools/modules/validation.py",
]

EXCLUDED_RELEASE_PY_FILES = {
    "check_js.py",
    "check_js2.py",
    "check_js3.py",
    "check_triple.py",
    "run_smoke_tests.py",
    "runner.py",
    "cloud_backup.py",
}


def read_text(name):
    return (ROOT / name).read_text(encoding="utf-8-sig")


def fail(failures, message):
    failures.append(message)
    print(f"FAIL {message}")


def ok(message):
    print(f"PASS {message}")


def test_python_syntax(failures):
    for name in PYTHON_FILES + DEV_TOOL_PYTHON_FILES:
        path = ROOT / name
        if not path.exists():
            fail(failures, f"missing Python source: {name}")
            continue
        try:
            ast.parse(read_text(name), filename=str(path))
            ok(f"Python syntax parses: {name}")
        except SyntaxError as exc:
            fail(failures, f"syntax error in {name}: {exc}")


def test_generated_app_javascript_parses(failures):
    node = shutil.which("node")
    if not node:
        fail(failures, "Node.js is required for generated app JavaScript syntax checking")
        return

    try:
        from ui_main import build_main_app_html

        try:
            app_config = json.loads(read_text("config/config.json"))
        except json.JSONDecodeError:
            app_config = {}
        css_content = read_text("style.css")
        html = build_main_app_html(
            css_content,
            app_config,
            "smoke-test",
            "smoke-test",
            "",
            "smoke-test",
        )
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S | re.I)
        if len(scripts) < 2:
            fail(failures, "generated app HTML does not contain the expected app script")
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "generated_app_script.js"
            script_path.write_text(scripts[-1], encoding="utf-8")
            result = subprocess.run(
                [node, "--check", str(script_path)],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                timeout=20,
            )
        if result.returncode == 0:
            ok("generated app JavaScript parses with node --check")
        else:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            fail(failures, "generated app JavaScript syntax check failed: " + (detail[0] if detail else "unknown error"))
    except Exception as exc:
        fail(failures, f"generated app JavaScript check crashed: {exc}")


def test_version_metadata(failures):
    try:
        data = json.loads(read_text("app_version.json"))
    except json.JSONDecodeError as exc:
        fail(failures, f"app_version.json is invalid JSON: {exc}")
        return

    version = str(data.get("version") or "").strip()
    prompt_version = str(data.get("global_stats_prompt_version") or "").strip()
    remote_management_url = str(data.get("remote_management_url") or "").strip()
    if version:
        ok(f"app version is set: {version}")
    else:
        fail(failures, "app version is missing")

    if prompt_version:
        ok(f"global stats prompt version is set: {prompt_version}")
    else:
        fail(failures, "global stats prompt version is missing")

    if remote_management_url:
        ok(f"remote management URL is set: {remote_management_url}")
    else:
        fail(failures, "remote management URL is missing")


def test_core_assets(failures):
    for name in ["custom_camos.json", "style.css", "setup.css", "xp_requirements.csv", "chart.js", "default_tactical_background.jpg", "default_tactical_background.png"]:
        path = ROOT / name
        if path.is_file() and path.stat().st_size > 0:
            ok(f"required file exists: {name}")
        else:
            fail(failures, f"missing or empty required file: {name}")

    for name in ["camoimages", "callingcards", "emblems", "locales", "perk icons", "rank icons", "themes"]:
        path = ROOT / name
        if path.is_dir() and any(item.is_file() for item in path.rglob("*")):
            ok(f"required asset directory has files: {name}")
        else:
            fail(failures, f"missing or empty asset directory: {name}")


def test_xp_csv_contract(failures):
    path = ROOT / "xp_requirements.csv"
    if not path.exists():
        fail(failures, "missing xp_requirements.csv")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        first_data = next(reader, None)

    expected = [
        "Stage",
        "Level",
        "Total XP in Current Stage",
        "Global Cumulative XP",
        "Legend 1 XP",
        "Legend 2 XP",
    ]
    if header == expected:
        ok("xp_requirements.csv header matches expected contract")
    else:
        fail(failures, f"unexpected xp_requirements.csv header: {header}")

    if first_data and len(first_data) >= 6:
        ok("xp_requirements.csv has data rows")
    else:
        fail(failures, "xp_requirements.csv has no usable data rows")


def test_camo_processor_contract(failures):
    bo3_tree = ast.parse(read_text("bo3tracker.py"), filename="bo3tracker.py")
    camo_tree = ast.parse(read_text("camo_processor.py"), filename="camo_processor.py")

    bo3_defs = {node.name for node in bo3_tree.body if isinstance(node, ast.FunctionDef)}
    camo_defs = {node.name for node in camo_tree.body if isinstance(node, ast.FunctionDef)}

    if "process_camo_data" in bo3_defs:
        ok("bo3tracker.py keeps process_camo_data compatibility wrapper")
    else:
        fail(failures, "bo3tracker.py missing process_camo_data wrapper")

    if "process_camo_data" in camo_defs:
        ok("camo_processor.py owns process_camo_data implementation")
    else:
        fail(failures, "camo_processor.py missing process_camo_data implementation")

    bo3_text = read_text("bo3tracker.py")
    camo_text = read_text("camo_processor.py")
    for required in [
        "from camo_processor import process_camo_data as build_camo_data",
        "return build_camo_data(user_json_path, app_config.get('starred', []))",
    ]:
        if required in bo3_text:
            ok(f"bo3tracker.py preserves camo wrapper contract: {required}")
        else:
            fail(failures, f"bo3tracker.py missing camo wrapper contract: {required}")

    for required in [
        "CAMO_ICON_CACHE",
        "CAMO_DB_FILE",
        "CAMO_NAMES",
        "get_camo_image_src",
        '"is_starred": w_id in starred_set',
    ]:
        if required in camo_text:
            ok(f"camo_processor.py includes camo behavior: {required}")
        else:
            fail(failures, f"camo_processor.py missing camo behavior: {required}")


def test_best_matches_contract(failures):
    bo3_text = read_text("bo3tracker.py")
    helper_text = read_text("best_matches.py")
    helper_tree = ast.parse(helper_text, filename="best_matches.py")
    helper_defs = {node.name for node in helper_tree.body if isinstance(node, ast.FunctionDef)}

    for required in [
        "get_game_summary",
        "load_best_matches",
        "save_best_matches",
        "find_archive_data",
        "sanitize_game_id",
        "add_best_match_from_data",
        "get_best_matches_with_archive_status",
        "remove_best_match_by_id",
    ]:
        if required in helper_defs:
            ok(f"best_matches.py exposes helper: {required}")
        else:
            fail(failures, f"best_matches.py missing helper: {required}")

    for required in [
        "add_best_match_from_data",
        "find_archive_data",
        "get_best_matches_with_archive_status",
        "remove_best_match_by_id",
        "sanitize_game_id",
    ]:
        if required in bo3_text:
            ok(f"bo3tracker.py delegates best-match behavior: {required}")
        else:
            fail(failures, f"bo3tracker.py missing best-match delegation: {required}")

    for removed in [
        "matches.insert(0, summary)",
        "updated = [m for m in matches",
        "result.setdefault(\"map\", \"Unknown Map\")",
    ]:
        if removed not in bo3_text:
            ok(f"bo3tracker.py no longer owns best-match list logic: {removed}")
        else:
            fail(failures, f"bo3tracker.py still owns best-match list logic: {removed}")


def test_player_stats_backup_contract(failures):
    bo3_text = read_text("bo3tracker.py")
    helper_text = read_text("player_stats_backup.py")
    helper_tree = ast.parse(helper_text, filename="player_stats_backup.py")
    helper_defs = {node.name for node in helper_tree.body if isinstance(node, ast.FunctionDef)}

    for required in [
        "get_players_dir",
        "find_player_stats_files",
        "normalize_backup_path",
        "create_player_stats_backup",
        "restore_player_stats_backup",
    ]:
        if required in helper_defs:
            ok(f"player_stats_backup.py exposes helper: {required}")
        else:
            fail(failures, f"player_stats_backup.py missing helper: {required}")

    for required in [
        "stats_zm_",
        "zipfile.ZipFile",
        "ZIP_DEFLATED",
    ]:
        if required in helper_text:
            ok(f"player_stats_backup.py includes backup behavior: {required}")
        else:
            fail(failures, f"player_stats_backup.py missing backup behavior: {required}")

    system_text = read_text("api_system.py")
    bo3_or_system = bo3_text + system_text
    for required in [
        "create_player_stats_backup",
        "find_player_stats_files",
        "normalize_backup_path",
        "restore_player_stats_backup",
        "players_dir, files_to_backup = find_player_stats_files(live_path)",
        "save_path = normalize_backup_path(save_path)",
        "create_player_stats_backup(files_to_backup, save_path)",
        "restore_player_stats_backup(zip_path, live_path)",
    ]:
        if required in bo3_or_system:
            ok(f"bo3tracker.py delegates player stats backup behavior: {required}")
        else:
            fail(failures, f"bo3tracker.py missing player stats backup delegation: {required}")


def test_best_match_sanitizer_behavior(failures):
    namespace = {}
    exec(compile(read_text("best_matches.py"), "best_matches.py", "exec"), namespace)
    sanitize_game_id = namespace["sanitize_game_id"]

    cases = {
        "x87:57889abdd43c25a3_155a_608ecbe3": "x87_57889abdd43c25a3_155a_608ecbe3",
        "bad|slash/name\\test": "bad_slash_name_test",
    }
    for raw, expected in cases.items():
        actual = sanitize_game_id(raw)
        if actual == expected:
            ok(f"best_matches.py sanitizes archive game ID: {raw}")
        else:
            fail(failures, f"best_matches.py sanitizer returned {actual!r}, expected {expected!r}")


def test_runner_contract(failures):
    runner_text = read_text("runner.py")
    release_sources = [name for name in PYTHON_FILES if name not in {"runner.py", "cloud_backup.py"}]
    for source_file in release_sources:
        if f'"{source_file}"' in runner_text:
            ok(f"runner.py copies source file: {source_file}")
        else:
            fail(failures, f"runner.py does not copy source file: {source_file}")

    if '"cloud_backup.py"' not in runner_text:
        ok("runner.py keeps inactive cloud_backup.py out of release copy list")
    else:
        fail(failures, "runner.py unexpectedly copies inactive cloud_backup.py")

    for asset in [
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
        "xp_requirements.csv",
        "chart.js",
        "default_tactical_background.jpg",
        "default_tactical_background.png",
    ]:
        if f'"{asset}"' in runner_text:
            ok(f"runner.py packages asset: {asset}")
        else:
            fail(failures, f"runner.py missing packaged asset: {asset}")

    for config_seed in [
        "config/map_challenges.json",
        "config/map_weapons.json",
        "config/uem_base_weapons.json",
        "config/uem_explosives.json",
    ]:
        if f'"{config_seed}"' in runner_text:
            ok(f"runner.py packages safe config seed: {config_seed}")
        else:
            fail(failures, f"runner.py missing safe config seed: {config_seed}")

    for label, safety_marker in [
        ("DB_PASS", '"DB" + "_PASS"'),
        ("uemmmiao_statsadmin", '"uemmmiao" + "_statsadmin"'),
        ("GLOBAL_STATS_INGEST_TOKEN =", '"GLOBAL_STATS_INGEST_TOKEN ="'),
        ("contributor_tokens", '"contributor_tokens"'),
    ]:
        if safety_marker in runner_text:
            ok(f"runner.py blocks private marker during source copy: {label}")
        else:
            fail(failures, f"runner.py missing private marker block: {label}")

    for required in ["assert_build_dependencies", '"webview", "pywebview"', "tk.Tk()", "BO3TRACKER_SLIM_REWARDS"]:
        if required in runner_text:
            ok(f"runner.py includes slim build guard: {required}")
        else:
            fail(failures, f"runner.py missing slim build guard: {required}")

    if '"HELP_FAQ.md"' in runner_text:
        ok("runner.py packages standalone Help & FAQ document")
    else:
        fail(failures, "runner.py missing packaged HELP_FAQ.md document")

    slim_bat = ROOT / "run_slim_runner.bat"
    if slim_bat.exists():
        slim_text = slim_bat.read_text(encoding="utf-8", errors="replace")
        for required in ["BO3TRACKER_SLIM_REWARDS=1", "BO3TRACKER_PYTHON", "LOCAL_PYTHON", "import PyInstaller, webview, tkinter as tk"]:
            if required in slim_text:
                ok(f"run_slim_runner.bat includes: {required}")
            else:
                fail(failures, f"run_slim_runner.bat missing: {required}")
    else:
        fail(failures, "missing run_slim_runner.bat")


def test_updater_managed_paths_cover_runner_assets(failures):
    runner_text = read_text("runner.py")
    updater_text = read_text("updater.py")

    runner_assets = set()
    in_assets = False
    for line in runner_text.splitlines():
        stripped = line.strip()
        if stripped == "assets_to_copy = [":
            in_assets = True
            continue
        if in_assets:
            if stripped == "]":
                break
            name = stripped.strip('",')
            if name:
                runner_assets.add(name)

    skipped = {"themes/grafftiimage.png"}
    managed_list = []
    in_managed = False
    for line in updater_text.splitlines():
        stripped = line.strip()
        if stripped == "MANAGED_PATHS = [":
            in_managed = True
            continue
        if in_managed:
            if stripped == "]":
                break
            name = stripped.strip('",')
            if name:
                managed_list.append(name)

    managed_set = set(managed_list)
    for asset in sorted(runner_assets - skipped):
        if asset in managed_set:
            ok(f"updater.py MANAGED_PATHS covers runner asset: {asset}")
        else:
            fail(failures, f"updater.py MANAGED_PATHS missing runner asset: {asset}")

    if "PRESERVED_CHILD_PATHS" in updater_text and '"themes": ["icon_cache"]' in updater_text:
        ok("updater.py preserves cached hosted theme icons/fonts inside themes/icon_cache")
    else:
        fail(failures, "updater.py does not preserve themes/icon_cache during theme folder updates")


def test_theme_contracts(failures):
    game_data_text = read_text("game_data.py")
    overlay_text = read_text("overlay_themes.py")
    ui_text = read_text("ui_main.py")

    for theme in ["Clouds", "Dog Pack", "DeadOps Arcade", "Extinction", "Pacific Paradise", "Shi No Numa"]:
        if theme in game_data_text:
            ok(f"game_data.py marks always-available theme: {theme}")
        else:
            fail(failures, f"game_data.py missing always-available theme: {theme}")

    for theme in ["Clouds", "Dog Pack", "Extinction", "Shi No Numa"]:
        if f'"{theme}"' in overlay_text or f"'{theme}'" in overlay_text:
            ok(f"overlay_themes.py includes overlay palette: {theme}")
        else:
            fail(failures, f"overlay_themes.py missing overlay palette: {theme}")

        if f'"{theme}"' in ui_text or f"'{theme}'" in ui_text or f"{theme}:" in ui_text:
            ok(f"ui_main.py includes graph/settings theme support: {theme}")
        else:
            fail(failures, f"ui_main.py missing graph/settings theme support: {theme}")


def test_compact_mode_contract(failures):
    api_text = read_text("api_display.py")
    ui_text = read_text("ui_main.py")
    css_text = read_text("style.css")

    checks = [
        ("api_display.py exposes compact mode getter", api_text, "def get_compact_mode"),
        ("api_display.py exposes compact mode setter", api_text, "def set_compact_mode"),
        ("ui_main.py renders Compact Mode control", ui_text, "compact-mode-toggle"),
        ("ui_main.py applies compact body class", ui_text, "document.body.classList.toggle('compact-mode'"),
        ("style.css defines compact mode layout", css_text, "body.compact-mode .sidebar"),
        ("style.css tightens compact cards", css_text, "body.compact-mode .card"),
    ]
    for label, text, needle in checks:
        if needle in text:
            ok(label)
        else:
            fail(failures, label)


def test_management_tools_contract(failures):
    required_files = [
        "dev_tools/README.md",
        "dev_tools/admin_gui.py",
        "dev_tools/modules/challenge_catalog.py",
        "dev_tools/modules/challenge_difficulty.py",
        "dev_tools/modules/challenge_manifest.py",
        "dev_tools/modules/global_stats_control.py",
        "dev_tools/modules/remote_management_manifest.py",
        "dev_tools/modules/validation.py",
    ]
    for name in required_files:
        if (ROOT / name).exists():
            ok(f"management tool file exists: {name}")
        else:
            fail(failures, f"missing management tool file: {name}")

    gui_text = read_text("dev_tools/admin_gui.py")
    for required in [
        "Global Stats",
        "Challenges",
        "Weekly Templates",
        "Map Challenges",
        "Checks",
        "Run Smoke Tests",
        "Save Control JSON",
        "Save Manifest",
        "Use As Template",
        "Add Copy To Manifest",
        "Compare With Editor",
        "Target multiplier",
        "Clear Active Weekly",
        "Load Current Into Manifest",
        "Preview Harder Targets",
        "Apply Preview",
        "Save Remote Config",
        "Save Weekly Templates",
        "Fetch Name",
        "Use Stat Template",
        "Save Map Challenges",
    ]:
        if required in gui_text:
            ok(f"management GUI exposes control: {required}")
        else:
            fail(failures, f"management GUI missing control: {required}")

    difficulty_text = read_text("dev_tools/modules/challenge_difficulty.py")
    for required in ["scale_target", "scale_challenge_targets", "preview_changes"]:
        if required in difficulty_text:
            ok(f"management difficulty helper includes: {required}")
        else:
            fail(failures, f"management difficulty helper missing: {required}")

    catalog_text = read_text("dev_tools/modules/challenge_catalog.py")
    for required in ["load_current_challenges", "load_default_challenges", "clone_for_manifest", "compare_challenges"]:
        if required in catalog_text:
            ok(f"management challenge catalog includes: {required}")
        else:
            fail(failures, f"management challenge catalog missing: {required}")

    validation_text = read_text("dev_tools/modules/validation.py")
    for required in ["ALLOWED_STATS", "ALLOWED_CATEGORIES", "discover_calling_cards", "discover_emblems", "discover_themes", "validate_manifest"]:
        if required in validation_text:
            ok(f"management validator includes: {required}")
        else:
            fail(failures, f"management validator missing: {required}")
    for required in ["RESERVED_LEVEL_EMBLEMS", "discover_all_emblems", "is_reserved_level_emblem_reward", "reserved level-completion emblem"]:
        if required in validation_text:
            ok(f"management validator protects level-completion emblems: {required}")
        else:
            fail(failures, f"management validator missing level emblem protection: {required}")

    manifest_text = read_text("dev_tools/modules/challenge_manifest.py")
    if "blank_weekly_challenge" in manifest_text:
        ok("management manifest helper includes weekly template")
    else:
        fail(failures, "management manifest helper missing weekly template")
    if "generate_random_weekly" in manifest_text:
        ok("management manifest helper includes random weekly generator")
    else:
        fail(failures, "management manifest helper missing random weekly generator")
    if "WEEKLY_TEMPLATES" in manifest_text:
        ok("challenge_manifest.py defines WEEKLY_TEMPLATES pool")
    else:
        fail(failures, "challenge_manifest.py missing WEEKLY_TEMPLATES pool")
    if "RESERVED_LEVEL_EMBLEMS" in manifest_text and "set(emblems) - RESERVED_LEVEL_EMBLEMS" in manifest_text:
        ok("challenge_manifest.py excludes level-completion emblems from random weekly rewards")
    else:
        fail(failures, "challenge_manifest.py can still choose reserved level-completion emblems")
    if '"stat": "headshots", "target_range": (2000, 2000)' in manifest_text and "Gumball Addict" not in manifest_text:
        ok("challenge_manifest.py random weekly pool replaces GobbleGums with 2,000 headshots")
    else:
        fail(failures, "challenge_manifest.py random weekly pool still has GobbleGums or lacks 2,000 headshots")

    remote_manifest_text = read_text("dev_tools/modules/remote_management_manifest.py")
    for required in [
        'challenge.get("cat") == "weekly"',
        'rotation.get("pool", [])',
        '"enabled": bool(weekly_pool)',
        '"pool": weekly_pool',
        "_strip_reserved_level_emblem_reward",
    ]:
        if required in remote_manifest_text:
            ok(f"remote management exports weekly pool: {required}")
        else:
            fail(failures, f"remote management missing weekly pool export: {required}")

    admin_text = read_text("dev_tools/admin_gui.py")
    if '"weekly_pool_count"' in admin_text:
        ok("admin_gui.py reports weekly pool count when saving remote config")
    else:
        fail(failures, "admin_gui.py does not report weekly pool count")

    gui_text = read_text("dev_tools/admin_gui.py")
    if "Random Weekly" in gui_text:
        ok("management GUI exposes Random Weekly button")
    else:
        fail(failures, "management GUI missing Random Weekly button")
    if "Clear Active Weekly" in gui_text and "_clear_active_weekly_challenges" in gui_text:
        ok("management GUI exposes Clear Active Weekly button")
    else:
        fail(failures, "management GUI missing Clear Active Weekly button")
    if "map_challenges.json" in gui_text and "_build_map_challenges_tab" in gui_text:
        ok("management GUI exposes map challenge editor")
    else:
        fail(failures, "management GUI missing map challenge editor")
    if "MAP_STAT_TEMPLATES" in gui_text and "_apply_map_stat_template" in gui_text:
        ok("management GUI exposes map stat templates")
    else:
        fail(failures, "management GUI missing map stat templates")

    weekly_text = read_text("dev_tools/modules/local_weekly_templates.py")
    for required in ["load_local_weekly_templates", "save_local_weekly_templates", "LOCAL_WEEKLY_TEMPLATES"]:
        if required in weekly_text:
            ok(f"management local weekly helper includes: {required}")
        else:
            fail(failures, f"management local weekly helper missing: {required}")

    remote_manifest_text = read_text("dev_tools/modules/remote_management_manifest.py")
    for required in ["build_remote_management", "save_remote_management", "global_stats", "challenges"]:
        if required in remote_manifest_text:
            ok(f"management remote export includes: {required}")
        else:
            fail(failures, f"management remote export missing: {required}")

    bo3_text = read_text("bo3tracker.py")
    network_text = read_text("api_network.py")
    bo3_or_network = bo3_text + network_text
    for required in [
        "REMOTE_MANAGEMENT_URL",
        "fetch_remote_management",
        "refresh_remote_management",
        "apply_remote_management",
        "refresh_remote_management_api",
        "get_global_stats_management_control_path",
        "get_global_stats_management_control",
        "get_global_stats_management_message",
        "management_outputs",
        "Anonymous global stats are currently disabled by management tools.",
    ]:
        if required in bo3_or_network:
            ok(f"bo3tracker.py respects management global-stats control: {required}")
        else:
            fail(failures, f"bo3tracker.py missing management global-stats control: {required}")

    remote_client_text = read_text("remote_management_client.py")
    for required in ["normalize_management", "load_cached_management", "fetch_remote_management"]:
        if required in remote_client_text:
            ok(f"remote management client includes: {required}")
        else:
            fail(failures, f"remote management client missing: {required}")

    discord_presence_text = read_text("discord_presence.py")
    if r"\\.\pipe\discord-ipc-{}" in discord_presence_text and r"\\?\pipe\discord-ipc-{}" in discord_presence_text:
        ok("discord_presence.py tries both known Windows Discord IPC pipe prefixes")
    else:
        fail(failures, "discord_presence.py is missing a Windows Discord IPC pipe prefix fallback")
    if "Make sure Discord is running" in discord_presence_text:
        ok("discord_presence.py shows a friendly Discord-not-running status")
    else:
        fail(failures, "discord_presence.py missing friendly Discord-not-running status")
    if "get_connection_diagnostics" in discord_presence_text and "last_attempted_pipes" in discord_presence_text:
        ok("discord_presence.py records Discord IPC connection diagnostics")
    else:
        fail(failures, "discord_presence.py missing Discord IPC connection diagnostics")

    challenge_manager_text = read_text("challenge_system.py")
    if "apply_remote_manifest" in challenge_manager_text:
        ok("challenge_system.py can apply remote manifests")
    else:
        fail(failures, "challenge_system.py missing remote manifest apply hook")
    for required in ["LEGEND_EMBLEM_UNLOCKS", "check_legend_emblem_unlocks_from_live_data", "prestige_legend"]:
        if required in challenge_manager_text:
            ok(f"challenge_system.py supports legend emblem unlocks: {required}")
        else:
            fail(failures, f"challenge_system.py missing legend emblem unlock support: {required}")
    if '"stat": "headshots", "target": 2000' in challenge_manager_text and "Weekly Precision" in challenge_manager_text:
        ok("challenge_system.py uses 2,000 headshot weekly template")
    else:
        fail(failures, "challenge_system.py missing 2,000 headshot weekly template")
    for title, target in [
        ("Weekly Deep Run", 50),
        ("Weekly Grinder", 30),
        ("Weekly Soda Run", 50),
        ("Weekly Addict", 100),
        ("Weekly Marathon", 50),
    ]:
        if f'"target": {target}' in challenge_manager_text and title in challenge_manager_text:
            ok(f"challenge_system.py keeps {title} at target {target}")
        else:
            fail(failures, f"challenge_system.py has an unexpected target for {title}")
    if "Weekly Chewer" not in challenge_manager_text and '"stat": "gobblegums_used", "target": 250' not in challenge_manager_text:
        ok("challenge_system.py no longer generates the GobbleGum weekly template")
    else:
        fail(failures, "challenge_system.py still includes the GobbleGum weekly template")
    for required in ["RESERVED_LEVEL_EMBLEMS", "is_reserved_level_emblem", "strip_reserved_level_emblem_reward"]:
        if required in challenge_manager_text:
            ok(f"challenge_system.py reserves legend emblems for level completion: {required}")
        else:
            fail(failures, f"challenge_system.py missing level-only emblem guard: {required}")
    for required in ["_repair_missing_reward_assignments", "_reward_asset_exists", "_replacement_reward_for", "_scan_available_reward_assets", "reward_pending"]:
        if required in challenge_manager_text:
            ok(f"challenge_system.py repairs deleted reward assignments: {required}")
        else:
            fail(failures, f"challenge_system.py missing deleted reward repair helper: {required}")
    if "sync_hosted_reward_assets" in challenge_manager_text and "_sync_hosted_rewards_once" in challenge_manager_text:
        ok("challenge_system.py syncs hosted reward assets before scanning reward pools")
    else:
        fail(failures, "challenge_system.py does not sync hosted reward assets before reward selection")
    if "previous_pending and incoming_has_final_reward" in challenge_manager_text and "_pending_reward_pair" in challenge_manager_text and "_pending_reward_type" in challenge_manager_text:
        ok("challenge_system.py lets remote map rewards replace pending placeholders")
    else:
        fail(failures, "challenge_system.py may preserve pending map rewards over final remote rewards")
    if "replacement = self._replacement_reward_for(pending_type, used_pairs" in challenge_manager_text:
        ok("challenge_system.py can dynamically assign unused rewards to pending map challenges")
    else:
        fail(failures, "challenge_system.py cannot dynamically assign unused rewards to pending map challenges")
    if "get_synced_hosted_reward_assets" in challenge_manager_text and "hosted_only=True" in challenge_manager_text:
        ok("challenge_system.py limits pending/repaired reward auto-pick to synced hosted assets")
    else:
        fail(failures, "challenge_system.py may auto-pick bundled local rewards for pending map rewards")

    validation_text = read_text("dev_tools/modules/validation.py")
    if "reward_pending" in validation_text and "not reward_pending" in validation_text:
        ok("management validation allows pending reward placeholders")
    else:
        fail(failures, "management validation may reject pending reward placeholders")

    try:
        map_challenge_data = json.loads(read_text("config/map_challenges.json"))
        map_challenges = map_challenge_data.get("challenges", [])
    except json.JSONDecodeError as exc:
        fail(failures, f"config/map_challenges.json is invalid JSON: {exc}")
        map_challenges = []

    giant_challenges = [
        item for item in map_challenges
        if isinstance(item, dict) and item.get("map_steam_link") == "zm_factory"
    ]
    if len(giant_challenges) == 12:
        ok("config/map_challenges.json includes 12 The Giant base-map challenges")
    else:
        fail(failures, f"config/map_challenges.json expected 12 The Giant challenges, found {len(giant_challenges)}")
    for required_id in ["map_zm_factory_01", "map_zm_factory_10", "map_zm_factory_11", "map_zm_factory_12"]:
        if any(item.get("id") == required_id for item in giant_challenges):
            ok(f"The Giant challenge exists: {required_id}")
        else:
            fail(failures, f"The Giant challenge missing: {required_id}")
    if giant_challenges and all(item.get("reward_pending") is True for item in giant_challenges):
        ok("The Giant rewards are marked as pending hosted assets")
    else:
        fail(failures, "The Giant rewards are not consistently marked reward_pending")
    if giant_challenges and all(item.get("reward_type") == "none" and item.get("pending_reward_type") == "emblem" and item.get("pending_reward_val") == "" for item in giant_challenges):
        ok("The Giant pending rewards dynamically choose unused emblem rewards")
    else:
        fail(failures, "The Giant pending rewards should use auto-pick pending emblem rewards and no active reward")
    for console_name in ["tesla_gun", "hero_annihilator", "lmg_slowfire"]:
        if any(item.get("weapon_console_name") == console_name for item in giant_challenges):
            ok(f"The Giant weapon challenge targets {console_name}")
        else:
            fail(failures, f"The Giant weapon challenge missing {console_name}")

    site_map_challenge_path = ROOT / "site" / "public_html" / "tracker" / "map_challenges.json"
    if site_map_challenge_path.exists():
        try:
            site_map_challenge_data = json.loads(site_map_challenge_path.read_text(encoding="utf-8"))
            site_map_challenges = site_map_challenge_data.get("challenges", [])
        except json.JSONDecodeError as exc:
            fail(failures, f"site map_challenges.json is invalid JSON: {exc}")
            site_map_challenges = []

        local_map_ids = {
            item.get("id")
            for item in map_challenges
            if isinstance(item, dict) and item.get("id")
        }
        site_map_ids = {
            item.get("id")
            for item in site_map_challenges
            if isinstance(item, dict) and item.get("id")
        }
        missing_site_ids = sorted(local_map_ids - site_map_ids)
        if not missing_site_ids:
            ok("site map_challenges.json includes every local map challenge")
        else:
            preview = ", ".join(missing_site_ids[:8])
            if len(missing_site_ids) > 8:
                preview += f", and {len(missing_site_ids) - 8} more"
            fail(failures, f"site map_challenges.json is missing local challenge IDs: {preview}")

        site_giant_challenges = [
            item for item in site_map_challenges
            if isinstance(item, dict) and item.get("map_steam_link") == "zm_factory"
        ]
        if site_giant_challenges and all(
            item.get("reward_type") == "none"
            and item.get("reward_pending") is True
            and item.get("pending_reward_type") == "emblem"
            and item.get("pending_reward_val") == ""
            for item in site_giant_challenges
        ):
            ok("site map_challenges.json keeps The Giant pending rewards dynamic")
        else:
            fail(failures, "site map_challenges.json does not keep The Giant pending rewards dynamic")

    reward_assets_text = read_text("reward_assets.py")
    for required in ["REWARD_MANIFEST_FILES", "get_hosted_reward_assets", "get_cached_hosted_reward_assets", "get_synced_hosted_reward_assets", "get_hosted_reward_sync_status", "sync_hosted_reward_assets", "_scrape_directory_assets", "sync_theme_referenced_assets", "prepare_theme_css_for_display", "icon_cache"]:
        if required in reward_assets_text:
            ok(f"reward_assets.py supports hosted reward sync: {required}")
        else:
            fail(failures, f"reward_assets.py missing hosted reward sync helper: {required}")
    for required in ['"running": False', '"downloaded": 0', '"pruned": 0', "Checking hosted reward assets", "Reward assets ready"]:
        if required in reward_assets_text:
            ok(f"reward_assets.py exposes hosted reward startup progress: {required}")
        else:
            fail(failures, f"reward_assets.py missing hosted reward startup progress: {required}")
    for required in [
        "SYNC_INDEX_FILE = \"hosted_reward_assets.json\"",
        "protected_app_version",
        "_ensure_protected_reward_baseline",
        "_record_synced_reward_assets",
        "_prune_stale_synced_reward_assets",
        "_safe_local_reward_path",
        "stale removed",
    ]:
        if required in reward_assets_text:
            ok(f"reward_assets.py prunes stale hosted rewards safely: {required}")
        else:
            fail(failures, f"reward_assets.py missing stale hosted reward cleanup: {required}")

    display_text = read_text("api_display.py")
    if "check_legend_emblem_unlocks_from_live_data" in display_text:
        ok("api_display.py refreshes legend emblem unlocks when loading emblems")
    else:
        fail(failures, "api_display.py does not refresh legend emblem unlocks when loading emblems")
    if "is_reserved_level_emblem" in display_text:
        ok("api_display.py ignores reserved legend emblems from completed challenge rewards")
    else:
        fail(failures, "api_display.py may expose reserved legend emblems from challenge rewards")
    unlocked_rewards_loop = display_text.split("for c in _reward_challenges():", 1)[0]
    if "not is_reserved_level_emblem(\"emblem\", emblem_name)" not in unlocked_rewards_loop:
        ok("api_display.py allows level-unlocked legend emblems in the emblem selector")
    else:
        fail(failures, "api_display.py hides level-unlocked legend emblems from the emblem selector")
    for required in ["def _asset_exists", "def _calling_card_exists", "def _emblem_exists", "get_unlocked_calling_cards", "get_unlocked_emblems"]:
        if required in display_text:
            ok(f"api_display.py filters reward selectors to existing asset files: {required}")
        else:
            fail(failures, f"api_display.py missing reward selector asset filter: {required}")
    if "allow_download=False" in display_text and "get_cached_hosted_reward_assets" in display_text and "_reward_challenges()" in display_text:
        ok("api_display.py keeps slim reward selectors fast while recognizing cached hosted emblems and calling cards")
    else:
        fail(failures, "api_display.py may block customization while checking hosted emblems/calling cards")
    if "sync_theme_referenced_assets(raw_css)" in display_text and "prepare_theme_css_for_display(raw_css)" in display_text:
        ok("api_display.py downloads and rewrites hosted theme references before inlining CSS")
    else:
        fail(failures, "api_display.py does not download and rewrite hosted theme references before inlining CSS")

    challenge_text = read_text("challenge_system.py")
    if "not c.get('cat') in ['daily', 'weekly']" not in challenge_text:
        ok("challenge_system.py preserves weekly/daily challenge categories")
    else:
        fail(failures, "challenge_system.py still strips weekly/daily challenge categories")

    ui_text = read_text("ui_main.py")
    for required in ["filterChallenges('weekly')", "currentChalFilter === 'weekly'"]:
        if required in ui_text:
            ok(f"ui_main.py exposes weekly challenges: {required}")
        else:
            fail(failures, f"ui_main.py missing weekly challenge support: {required}")
    if "Array.from(select.options).some(opt => opt.value === current)" in ui_text:
        ok("ui_main.py avoids blank reward selector values when an active reward was removed")
    else:
        fail(failures, "ui_main.py may still show blank reward selector values for removed active rewards")
    for required in ["scheduleCustomizationRefresh", "customizationRefreshToken", "[1500, 4000, 8000]"]:
        if required in ui_text:
            ok(f"ui_main.py refreshes customization after hosted reward downloads: {required}")
        else:
            fail(failures, f"ui_main.py missing customization refresh support: {required}")
    for required in ["startup-asset-sync", "startStartupAssetStatusPolling", "get_startup_asset_status", "Preparing Reward Assets"]:
        if required in ui_text:
            ok(f"ui_main.py shows hosted reward startup progress: {required}")
        else:
            fail(failures, f"ui_main.py missing hosted reward startup progress UI: {required}")
    for required in ["history-copy-btn", "copyHistoryGameId", "copyTextToClipboard", "Copy game ID"]:
        if required in ui_text:
            ok(f"ui_main.py can copy archived match game IDs: {required}")
        else:
            fail(failures, f"ui_main.py missing archived match game ID copy support: {required}")

    style_text = read_text("style.css")
    for required in ["history-row-actions", "history-copy-btn", "--success"]:
        if required in style_text:
            ok(f"style.css styles archived match game ID copy controls: {required}")
        else:
            fail(failures, f"style.css missing archived match game ID copy styling: {required}")

    system_text = read_text("api_system.py")
    if "get_startup_asset_status" in system_text and "get_hosted_reward_sync_status" in system_text:
        ok("api_system.py exposes hosted reward startup status to the UI")
    else:
        fail(failures, "api_system.py missing hosted reward startup status API")

    bo3_text = read_text("bo3tracker.py")
    if "schedule_hosted_reward_asset_sync" in bo3_text and "sync_hosted_reward_assets(force=False)" in bo3_text:
        ok("bo3tracker.py starts hosted reward sync in the background")
    else:
        fail(failures, "bo3tracker.py does not start hosted reward sync in the background")
    if "def main(on_app_ready=None)" in bo3_text and "set_startup_progress_callback" in bo3_text:
        ok("bo3tracker.py exposes startup hooks for the pre-window splash")
    else:
        fail(failures, "bo3tracker.py missing startup hooks for the pre-window splash")

    launcher_text = read_text("bo3tracker_launcher.py")
    for required in ["StartupSplash", "ttk.Progressbar", "mode=\"indeterminate\"", "def pump", "setup_window"]:
        if required in launcher_text:
            ok(f"bo3tracker_launcher.py shows pre-window startup progress: {required}")
        else:
            fail(failures, f"bo3tracker_launcher.py missing pre-window startup progress support: {required}")


def test_app_metadata_consistency(failures):
    version_data = json.loads(read_text("app_version.json"))
    app_version = str(version_data.get("version") or "").strip()

    metadata_text = read_text("app_metadata.py")
    for line in metadata_text.splitlines():
        line = line.strip()
        if line.startswith("DEFAULT_VERSION") and "=" in line:
            default_version = line.split("=", 1)[1].strip().strip("\"'")
            if default_version == app_version:
                ok(f"app_metadata.py DEFAULT_VERSION matches app_version.json: {default_version}")
            else:
                fail(failures, f"app_metadata.py DEFAULT_VERSION is {default_version!r}, but app_version.json has {app_version!r}")
            break


def test_ftp_uploader_contract(failures):
    ftp_path = ROOT / "dev_tools/modules/ftp_uploader.py"
    if not ftp_path.exists():
        fail(failures, "missing dev_tools/modules/ftp_uploader.py")
        return

    ftp_text = read_text("dev_tools/modules/ftp_uploader.py")
    for required in ["load_ftp_config", "save_ftp_config", "upload_file", "ftplib.FTP", "storbinary"]:
        if required in ftp_text:
            ok(f"ftp_uploader.py includes: {required}")
        else:
            fail(failures, f"ftp_uploader.py missing: {required}")

    gui_text = read_text("dev_tools/admin_gui.py")
    for required in ["FTP Upload", "Upload remote_management.json", "Test Connection", "Save Credentials"]:
        if required in gui_text:
            ok(f"admin_gui.py FTP tab exposes: {required}")
        else:
            fail(failures, f"admin_gui.py FTP tab missing: {required}")


def test_app_paths_contract(failures):
    paths_text = read_text("app_paths.py")
    for required in [
        "CONFIG_DIR_NAME",
        "get_config_dir",
        "get_runtime_path",
        "get_runtime_dir",
        "migrate_runtime_path",
        "migrate_all_runtime_paths",
    ]:
        if required in paths_text:
            ok(f"app_paths.py includes: {required}")
        else:
            fail(failures, f"app_paths.py missing: {required}")

    for filename in ["config.json", "best_matches.json", "challenges.json", "hosted_reward_assets.json", "map_challenges.json", "map_index_cache.json", "map_detail_summary.json"]:
        if filename in paths_text:
            ok(f"app_paths.py tracks runtime file: {filename}")
        else:
            fail(failures, f"app_paths.py missing runtime file: {filename}")

    bo3_text = read_text("bo3tracker.py")
    for required in ["migrate_all_runtime_paths", "get_runtime_path"]:
        if required in bo3_text:
            ok(f"bo3tracker.py uses app_paths: {required}")
        else:
            fail(failures, f"bo3tracker.py missing app_paths usage: {required}")


def test_api_data_map_index_contract(failures):
    api_text = read_text("api_data.py")
    for required in [
        "_ensure_map_index",
        "get_map_selection",
        "refresh_map_selection",
        "get_map_detail",
        "_compute_map_detail",
        "_ensure_map_detail_summary",
        "_map_index = None",
        "_index_file_count = 0",
        "_map_detail_cache = None",
        "_map_detail_summary = None",
        "_detail_summary_index_count = 0",
        "map_index_cache.json",
        "map_detail_summary.json",
    ]:
        if required in api_text:
            ok(f"api_data.py includes map index feature: {required}")
        else:
            fail(failures, f"api_data.py missing map index feature: {required}")


def test_api_data_pagination_contract(failures):
    api_text = read_text("api_data.py")
    # Check that get_map_detail signature has page/per_page params
    signature_checks = [
        'get_map_detail(self, map_name, player_id="0", page=1, per_page=25)',
    ]
    for sig in signature_checks:
        if sig in api_text:
            ok(f"api_data.py get_map_detail signature: {sig.split('(')[0]}(page=1, per_page=25)")
        else:
            fail(failures, f"api_data.py get_map_detail signature mismatch: {sig}")

    for field in ['"page": page', '"per_page": per_page', '"total_matches": total', '"has_more": has_more']:
        if field in api_text:
            ok(f"api_data.py get_map_detail returns pagination field: {field}")
        else:
            fail(failures, f"api_data.py get_map_detail missing pagination field: {field}")

    if 'page = max(1, int(page))' in api_text and 'per_page = max(1, min(100, int(per_page)))' in api_text:
        ok("api_data.py get_map_detail clamps page/per_page range")
    else:
        fail(failures, "api_data.py get_map_detail missing page/per_page clamping")


def test_api_data_map_detail_weapon_merge_contract(failures):
    api_text = read_text("api_data.py")
    for required in [
        "MAP_DETAIL_SUMMARY_VERSION = 2",
        "def _get_combined_weapon_data",
        'for source_key in ("weapon_data", "top5")',
        'for field in ("kills", "headshots", "damage")',
        "existing[field] = max(safe_int(existing.get(field)), safe_int(weapon.get(field)))",
        "weapons_data = self._get_combined_weapon_data(player)",
        "w_data = self._get_combined_weapon_data(p)",
        "weapons = self._get_combined_weapon_data(p)",
        "map_weapons_manager.load()",
        'cached.get("_version") == self.MAP_DETAIL_SUMMARY_VERSION',
        '"_version": self.MAP_DETAIL_SUMMARY_VERSION',
    ]:
        if required in api_text:
            ok(f"api_data.py map detail merges weapon sources: {required[:70]}")
        else:
            fail(failures, f"api_data.py map detail weapon merge missing: {required}")


def test_map_weapons_category_override_contract(failures):
    map_weapons_text = read_text("map_weapons.py")
    admin_text = read_text("dev_tools/admin_gui.py")
    weapon_categories_text = read_text("weapon_categories.py")
    for required in [
        "def set_weapon_category(self, steam_link, console_name, category, display_name=\"\")",
        "display_name = str(display_name or console_name).strip()",
        'entry["weapons"].append({',
        "# Exact per-map entries are manual overrides for a specific console stat row.",
        "# Finally, fall back to global/base weapons.",
        "def get_console_category_override(self, console_name)",
        "best_timestamp = -1",
    ]:
        if required in map_weapons_text:
            ok(f"map_weapons.py supports exact category overrides: {required[:70]}")
        else:
            fail(failures, f"map_weapons.py missing exact category override behavior: {required}")

    api_text = read_text("api_data.py")
    for required in [
        "console_category = map_weapons_manager.get_console_category_override(console_name)",
        "console_category = map_weapons_manager.get_console_category_override(matched_console_name)",
        "if console_category and console_category != \"other\":",
    ]:
        if required in api_text:
            ok(f"api_data.py applies console category overrides: {required}")
        else:
            fail(failures, f"api_data.py missing console category override usage: {required}")

    if "map_weapons_manager.set_weapon_category(link, cn, category, dn)" in admin_text:
        ok("admin_gui.py passes display name when saving map weapon category overrides")
    else:
        fail(failures, "admin_gui.py does not pass display name to map weapon category overrides")

    for required in [
        '"bouncingbetty": "explosive"',
        '"iw8_cr56": "assault_rifle"',
        '"h2_rpg7": "launcher"',
        '"t8_strife": "pistol"',
        '"wpn_custom_spoon_01": "melee"',
        '"iw7_xeon": "assault_rifle"',
    ]:
        if required in weapon_categories_text:
            ok(f"weapon_categories.py classifies known map weapon: {required}")
        else:
            fail(failures, f"weapon_categories.py missing known map weapon category: {required}")

    try:
        map_weapon_data = json.loads(read_text("config/map_weapons.json"))
    except json.JSONDecodeError as exc:
        fail(failures, f"config/map_weapons.json is invalid JSON: {exc}")
        map_weapon_data = {}

    known_map_weapon_categories = {
        "bouncingbetty": "explosive",
        "iw8_cr56": "assault_rifle",
        "h2_rpg7": "launcher",
        "t8_strife": "pistol",
        "wpn_custom_spoon_01": "melee",
        "iw7_xeon_up": "assault_rifle",
        "waw_ppsh": "smg",
    }
    all_map_weapons = [
        weapon
        for entry in map_weapon_data.values()
        for weapon in entry.get("weapons", [])
    ]
    for console_name, expected_category in known_map_weapon_categories.items():
        matching = [weapon for weapon in all_map_weapons if weapon.get("console_name") == console_name]
        if any(weapon.get("category") == expected_category for weapon in matching):
            ok(f"config/map_weapons.json backfills {console_name} as {expected_category}")
        else:
            fail(failures, f"config/map_weapons.json missing {console_name} category {expected_category}")


def test_ui_main_map_detail_frontend(failures):
    ui_text = read_text("ui_main.py")
    for required in [
        "async function loadMoreMapMatches",
        "map-detail-load-more-btn",
        "async function refreshMapSelection",
        "async function openMapSelectionPage",
        "async function openMapDetail",
        "await loadWeaponDetail(selectedWeaponDetailName, true)",
        "async function loadWeaponDetail(weaponName, preserveScroll=false)",
        "currentMapDetail && currentMapDetail.map",
        "mapSelectionData && mapSelectionData.length > 0",
    ]:
        if required in ui_text:
            ok(f"ui_main.py includes map detail UI: {required[:60]}")
        else:
            fail(failures, f"ui_main.py missing map detail UI: {required}")


def test_stats_processor_weapons_priority(failures):
    sp_text = read_text("stats_processor.py")
    target = "p.get('top5') or p.get('weapon_data') or {}"
    if target in sp_text:
        ok("stats_processor.py prefers top5 over weapon_data")
    else:
        fail(failures, "stats_processor.py wrong weapons priority (expected top5 before weapon_data)")


def test_map_challenge_ui_contract(failures):
    ui_text = read_text("ui_main.py")
    css_text = read_text("style.css")
    system_text = read_text("api_system.py")
    for required in [
        "renderOperationsChallenges",
        "isMapChallenge",
        "normalizeWorkshopLink",
        "map-challenge-section",
        "map-challenge-heading",
        "map-challenge-heading-link",
        "mapChallengeOpenGroups",
        "<details class=\"map-challenge-section\"",
        "setMapChallengeOpenState",
        "map-challenge-heading-progress",
    ]:
        if required in ui_text or required in css_text:
            ok(f"map challenge UI includes: {required}")
        else:
            fail(failures, f"map challenge UI missing: {required}")

    for required in [
        'id="mapcompat-btn" aria-disabled="true"',
        "DISABLED: WORKSHOP IMAGE SCRIPTS",
        "Map Compat is temporarily disabled until Steam Workshop image download scripts are fixed.",
        ".nav-btn.disabled",
    ]:
        if required in ui_text or required in css_text or required in system_text:
            ok(f"map compat disabled state includes: {required}")
        else:
            fail(failures, f"map compat disabled state missing: {required}")


def test_tracker_config_backup_contract(failures):
    bo3_text = read_text("bo3tracker.py")
    for required in [
        "RUNTIME_FILENAMES",
        "add_backup_file",
        "unlocked_rewards.json",
        "newest_path = max(candidates, key=lambda path: os.path.getmtime(path))",
        "challenge_manager.unlocked_rewards = challenge_manager._load_unlocks()",
    ]:
        if required in bo3_text:
            ok(f"tracker config backup includes: {required}")
        else:
            fail(failures, f"tracker config backup missing: {required}")


def test_workshop_images_contract(failures):
    wi_text = read_text("workshop_images.py")
    for required in [
        "get_workshop_image",
        "_scrape_image_url",
        "_download_image",
        "_get_cache_dir",
        "_cleanup_cache",
        "MAX_CACHE_SIZE_MB",
        "steamcommunity.com/sharedfiles/filedetails",
        "base64",
    ]:
        if required in wi_text:
            ok(f"workshop_images.py includes: {required}")
        else:
            fail(failures, f"workshop_images.py missing: {required}")

    bo3_text = read_text("bo3tracker.py")
    if "get_workshop_image" in bo3_text:
        ok("bo3tracker.py delegates to get_workshop_image")
    else:
        fail(failures, "bo3tracker.py missing get_workshop_image usage")


def test_global_stats_weapon_summary_contract(failures):
    namespace = {}
    exec(compile(read_text("global_stats_client.py"), "global_stats_client.py", "exec"), namespace)
    summarize_weapons = namespace["summarize_weapons"]
    summarize_match_file = namespace["summarize_match_file"]
    sync_history = namespace["sync_history"]

    players = {
        "0": {
            "top5": {
                "old_weapon": {"display": "Old Top5 Weapon", "kills": 999, "headshots": 1, "damage": 1}
            },
            "weapon_data": {
                f"weapon_{index}": {
                    "display": f"Weapon {index:02d}",
                    "kills": index,
                    "headshots": index // 2,
                    "damage": index * 10,
                }
                for index in range(1, 23)
            },
        }
    }

    weapons = summarize_weapons(players)
    names = {weapon["name"] for weapon in weapons}
    if len(weapons) == 22 and "Weapon 22" in names:
        ok("global stats uploads every weapon from merged weapon_data")
    else:
        fail(failures, "global stats weapon summary still clips merged weapon_data")

    if "Old Top5 Weapon" not in names:
        ok("global stats prefers merged weapon_data over stale top5")
    else:
        fail(failures, "global stats still prefers stale top5 over weapon_data")

    with tempfile.TemporaryDirectory() as temp_dir:
        match_path = Path(temp_dir) / "Game_version_check.json"
        match_path.write_text(json.dumps({
            "game": {
                "game_id": "version_check",
                "map_played": "Version Check",
                "rounds_total": 12,
                "time_total": 600,
            },
            "players": {
                "0": {"kills": 10, "headshots": 5}
            },
        }), encoding="utf-8")
        summary = summarize_match_file(match_path, {"install_id": "test-install"})
    if summary and summary.get("client_version") == namespace["APP_VERSION"]:
        ok("global stats match summary includes client_version for recent matches")
    else:
        fail(failures, "global stats match summary missing client_version")

    with tempfile.TemporaryDirectory() as temp_dir:
        low_round_path = Path(temp_dir) / "Game_low_round.json"
        low_round_path.write_text(json.dumps({
            "game": {
                "game_id": "low_round",
                "map_played": "Low Round",
                "rounds_total": 3,
                "time_total": 240,
            },
            "players": {
                "0": {"kills": 3, "headshots": 1}
            },
        }), encoding="utf-8")
        low_round_summary = summarize_match_file(low_round_path, {"install_id": "test-install"})
    if low_round_summary is None and "MIN_GLOBAL_STATS_ROUND = 4" in read_text("global_stats_client.py"):
        ok("global stats client skips matches before round 4")
    else:
        fail(failures, "global stats client may upload matches before round 4")

    global_stats_text = read_text("global_stats_client.py")
    if '"client_version": APP_VERSION' in global_stats_text and '"app_version": APP_VERSION' in global_stats_text:
        ok("global stats upload payload includes client_version alongside app_version")
    else:
        fail(failures, "global stats upload payload missing client_version")

    submit_stats_text = read_text("site/public_html/tracker/submit_stats.php")
    if (
        "MIN_GLOBAL_STATS_ROUND = 4" in submit_stats_text
        and "$roundReached < MIN_GLOBAL_STATS_ROUND" in submit_stats_text
        and "($accepted + $updated + $duplicates) > 0" in submit_stats_text
    ):
        ok("global stats ingest rejects matches before round 4")
    else:
        fail(failures, "global stats ingest may still accept matches before round 4")

    recent_matches_text = read_text("site/public_html/tracker/recent_matches.php")
    if "MIN_GLOBAL_STATS_ROUND = 4" in recent_matches_text and "m.round_reached >= :min_round" in recent_matches_text:
        ok("recent matches API filters out matches before round 4")
    else:
        fail(failures, "recent matches API may still show matches before round 4")

    global_stats_php_text = read_text("site/public_html/tracker/global_stats.php")
    if "MIN_GLOBAL_STATS_ROUND = 4" in global_stats_php_text and "WHERE round_reached >=" in global_stats_php_text and "m.round_reached >=" in global_stats_php_text:
        ok("global stats API filters aggregate and weapon results to round 4+")
    else:
        fail(failures, "global stats API may still include matches before round 4")

    uploaded = {"match_hash": "already_uploaded", "game_id_hash": "game_a"}
    fresh = {"match_hash": "fresh_match", "game_id_hash": "game_b"}
    captured = {}

    def fake_get_or_create_state(_state_path):
        return {"install_id": "test-install", "uploaded_match_hashes": ["already_uploaded"], "last_sync_at": 0}

    def fake_scan_history_folder(_history_path, _state, include_uploaded=False):
        return [uploaded, fresh]

    def fake_upload_summaries(state, summaries, profile_summaries=None, timeout=20):
        captured["summaries"] = list(summaries)
        captured["profile_summaries"] = list(profile_summaries or [])
        state["uploaded_match_hashes"] = [item["match_hash"] for item in summaries]
        return {"accepted": len(summaries), "updated": 0, "duplicates": 0}

    namespace["get_or_create_state"] = fake_get_or_create_state
    namespace["scan_history_folder"] = fake_scan_history_folder
    namespace["upload_summaries"] = fake_upload_summaries
    with tempfile.TemporaryDirectory() as temp_dir:
        result = sync_history(temp_dir, str(Path(temp_dir) / "state.json"), force=True)

    if result.get("ok") and [item["match_hash"] for item in captured.get("summaries", [])] == ["already_uploaded", "fresh_match"]:
        ok("forced global stats sync reuploads existing matches for weapon backfill")
    else:
        fail(failures, "forced global stats sync does not reupload existing matches")


def test_runner_source_completeness(failures):
    runner_text = read_text("runner.py")

    if 'MAIN_SCRIPT = "bo3tracker_launcher.py"' in runner_text:
        ok("runner.py builds the startup splash launcher as the app entry point")
    else:
        fail(failures, "runner.py does not build the startup splash launcher as the app entry point")

    root_py_files = {p.name for p in ROOT.glob("*.py") if p.is_file()}
    expected = root_py_files - EXCLUDED_RELEASE_PY_FILES

    for py_file in sorted(expected):
        if f'"{py_file}"' in runner_text:
            ok(f"runner.py includes source file: {py_file}")
        else:
            fail(failures, f"runner.py missing source file in scripts list: {py_file}")

    for excluded in EXCLUDED_RELEASE_PY_FILES:
        if f'"{excluded}"' not in runner_text:
            ok(f"runner.py correctly excludes: {excluded}")
        else:
            fail(failures, f"runner.py should NOT include excluded file: {excluded}")


def test_api_circular_import_safety(failures):
    api_files = ["api_data.py", "api_display.py", "api_network.py", "api_system.py"]

    for name in api_files:
        text = read_text(name)
        if "import sys" in text:
            ok(f"{name} imports sys (needed for _bt lambda)")
        else:
            fail(failures, f"{name} missing import sys")

        if "_bt = lambda: sys.modules[\"bo3tracker\"]" in text:
            ok(f"{name} uses _bt lazy import pattern")
        else:
            fail(failures, f"{name} missing _bt = lambda: sys.modules[\"bo3tracker\"]")

        if "import bo3tracker" in text:
            fail(failures, f"{name} still has 'import bo3tracker' at module level (causes circular import)")
        else:
            ok(f"{name} has no 'import bo3tracker' at module level")

    bo3_text = read_text("bo3tracker.py")
    if 'sys.modules["bo3tracker"] = sys.modules["__main__"]' in bo3_text:
        ok("bo3tracker.py registers __main__ as sys.modules['bo3tracker']")
    else:
        fail(failures, "bo3tracker.py missing __main__ alias for sys.modules['bo3tracker']")


def test_graph_overlay_contract(failures):
    # Graph overlay HTML builder exists
    graph_text = read_text("ui_views.py")
    if "def build_graph_overlay_html" in graph_text:
        ok("ui_views.py defines build_graph_overlay_html")
    else:
        fail(failures, "ui_views.py missing build_graph_overlay_html")

    # Graph overlay lifecycle in bo3tracker.py
    bo3_text = read_text("bo3tracker.py")
    for required in [
        "def get_graph_overlay_html",
        "def graph_overlay_loop",
        "def toggle_graph_overlay_logic",
        "def push_graph_overlay_theme",
        "def push_graph_overlay_scale",
        "graph_overlay_window = None",
        "stop_graph_overlay = False",
    ]:
        if required in bo3_text:
            ok(f"bo3tracker.py includes {required.split()[1]}")
        else:
            fail(failures, f"bo3tracker.py missing {required.split()[1]}")

    if "app_config.get('graph_overlay_enabled', False)" in bo3_text:
        ok("bo3tracker.py startup_checks reads graph_overlay_enabled")
    else:
        fail(failures, "bo3tracker.py startup_checks missing graph_overlay_enabled")

    for required in [
        "def get_saved_window_position",
        "def remember_window_position",
        "overlay_window_position",
        "graph_overlay_window_position",
        "window.screenX",
        "remember_window_position(unified_window, \"overlay_window_position\", force=True)",
    ]:
        if required in bo3_text:
            ok(f"bo3tracker.py persists overlay window positions: {required}")
        else:
            fail(failures, f"bo3tracker.py missing overlay position persistence: {required}")

    # api_system.py has graph overlay API methods
    system_text = read_text("api_system.py")
    for required in [
        "def toggle_graph_overlay_system",
        "def toggle_graph_overlay_component",
        '"xpm_graph", "roundxp_graph", "zpm_graph"',
    ]:
        if required in system_text:
            ok(f"api_system.py includes graph overlay method")
        else:
            fail(failures, f"api_system.py missing graph overlay method: {required}")

    # ui_main.py has graph overlay settings UI
    ui_text = read_text("ui_main.py")
    for required in [
        "toggleGraphOverlays(this)",
        "toggleGraphOverlayComponent('xpm_graph'",
        "toggleGraphOverlayComponent('roundxp_graph'",
        "toggleGraphOverlayComponent('zpm_graph'",
        "function toggleGraphOverlays",
        "function toggleGraphOverlayComponent",
    ]:
        if required in ui_text:
            ok(f"ui_main.py has graph overlay UI: {required[:60]}")
        else:
            fail(failures, f"ui_main.py missing graph overlay UI: {required}")

    # challenge overlay has its own window, API, and card selection controls
    for required in [
        "def build_challenge_overlay_html",
        "updateChallengeOverlay",
        "applyChallengeOverlayTheme",
        "setChallengeOverlayScale",
    ]:
        if required in graph_text:
            ok(f"ui_views.py includes challenge overlay HTML: {required}")
        else:
            fail(failures, f"ui_views.py missing challenge overlay HTML: {required}")

    for required in [
        "challenge_overlay_window = None",
        "def normalise_challenge_overlay_ids",
        "def get_challenge_overlay_items",
        "def challenge_overlay_loop",
        "def toggle_challenge_overlay_logic",
        "challenge_overlay_window_position",
        "app_config.get('challenge_overlay_enabled', False)",
    ]:
        if required in bo3_text:
            ok(f"bo3tracker.py includes challenge overlay lifecycle: {required}")
        else:
            fail(failures, f"bo3tracker.py missing challenge overlay lifecycle: {required}")

    for required in [
        "def get_challenge_overlay_settings",
        "def toggle_challenge_overlay_system",
        "def set_challenge_overlay_selection",
    ]:
        if required in system_text:
            ok(f"api_system.py exposes challenge overlay API: {required}")
        else:
            fail(failures, f"api_system.py missing challenge overlay API: {required}")

    for required in [
        "challenge-overlay-toggle",
        "challengeOverlaySelectedIds",
        "refreshChallengeOverlaySettings",
        "toggleChallengeOverlaySelection",
        "challenge-track-btn",
        "You can track a maximum of 3 challenges at a time.",
    ]:
        if required in ui_text:
            ok(f"ui_main.py includes challenge overlay controls: {required}")
        else:
            fail(failures, f"ui_main.py missing challenge overlay controls: {required}")

    css_text = read_text("style.css")
    for required in [
        ".challenge-overlay-picker",
        ".challenge-overlay-pill",
        ".challenge-track-btn",
    ]:
        if required in css_text:
            ok(f"style.css styles challenge overlay controls: {required}")
        else:
            fail(failures, f"style.css missing challenge overlay style: {required}")

    # chart.js asset is bundled
    if Path(ROOT / "chart.js").is_file():
        ok("chart.js asset file exists")
    else:
        fail(failures, "chart.js asset file missing")

    # weapon damage pie chart in career weapons page
    ui_text = read_text("ui_main.py")
    for required in [
        "weaponCategoryDamageChart",
        "weapon-category-damage-legend",
        "function renderWeaponCategoryDamageChart",
        "weaponCategoryDamageChartInstance",
        "renderWeaponCategoryDamageChart()",
    ]:
        if required in ui_text:
            ok(f"ui_main.py has weapon damage pie chart: {required}")
        else:
            fail(failures, f"ui_main.py missing weapon damage pie chart: {required}")

    # damage field in category_breakdown
    api_data_text = read_text("api_data.py")
    if '"damage": 0' in api_data_text or "'damage': 0" in api_data_text:
        ok("api_data.py category_breakdown includes damage field")
    else:
        fail(failures, "api_data.py category_breakdown missing damage field")


def test_career_profile_recent_additions(failures):
    ui_text = read_text("ui_main.py")
    api_data_text = read_text("api_data.py")
    api_system_text = read_text("api_system.py")
    css_text = read_text("style.css")
    faq_text = read_text("HELP_FAQ.md")

    for required in [
        "life_shot_acc",
        "life_shot_acc_row",
        "shots_hit",
        "shots_missed",
        "shots_fired",
    ]:
        if required in ui_text or required in api_data_text:
            ok(f"career shot accuracy wiring includes: {required}")
        else:
            fail(failures, f"career shot accuracy wiring missing: {required}")

    for required in [
        "let xpTrendTooltipRows = []",
        "function formatXpTrendAxisLabel",
        "maxRotation: 0",
        "autoSkipPadding: 22",
        "return row.date ? [row.map, row.date] : row.map",
    ]:
        if required in ui_text:
            ok(f"career XP trend labels include: {required}")
        else:
            fail(failures, f"career XP trend labels missing: {required}")

    if "return label.replace(/\\\\n.*/, '')" not in ui_text:
        ok("career XP trend no longer uses fragile generated regex tooltip stripping")
    else:
        fail(failures, "career XP trend still uses fragile generated regex tooltip stripping")

    for required in [
        "def get_diagnostics_status",
        "glob.glob(os.path.join(hist_path, \"Game_*.json\"))",
        "get_hosted_reward_sync_status",
        "global_stats_last_message",
    ]:
        if required in api_system_text:
            ok(f"diagnostics backend includes: {required}")
        else:
            fail(failures, f"diagnostics backend missing: {required}")

    for required in [
        "diagnostics-panel",
        "loadDiagnosticsPanel",
        "diagnostic-chip",
        "diagnostics-card",
    ]:
        if required in ui_text or required in css_text:
            ok(f"diagnostics frontend includes: {required}")
        else:
            fail(failures, f"diagnostics frontend missing: {required}")

    for required in [
        "https://discord.com/users/140242942773297153",
        "discord-contact-panel",
        "discord-contact-button",
        "discord-contact-icon",
        "discord-contact-action",
        "discord-contact-copy-btn",
        "copySupportDiscord",
        "GurtLushSalmon",
    ]:
        if required in ui_text or required in css_text:
            ok(f"help Discord contact UI includes: {required}")
        else:
            fail(failures, f"help Discord contact UI missing: {required}")

    for required in [
        "## Support Contact",
        "GurtLushSalmon",
        "Discord profile button",
        "https://discord.com/users/140242942773297153",
        "CurrentGame.json",
    ]:
        if required in faq_text:
            ok(f"HELP_FAQ.md includes: {required}")
        else:
            fail(failures, f"HELP_FAQ.md missing: {required}")

    namespace_backup = sys.modules.get("bo3tracker")
    try:
        from api_data import DataAPI

        with tempfile.TemporaryDirectory() as temp_dir:
            dummy = types.SimpleNamespace(
                app_config={"history_path": temp_dir},
                get_live_game_data=lambda: {
                    "players": {
                        "0": {
                            "shots_hit": 75,
                            "shots_missed": 25,
                            "shots_fired": 100,
                        }
                    }
                },
            )
            sys.modules["bo3tracker"] = dummy
            stats = DataAPI().get_lifetime_stats()
        if stats["ratios"]["shot_accuracy"] == 75.0:
            ok("career shot accuracy computes shots_hit / shots_fired")
        else:
            fail(failures, f"career shot accuracy returned unexpected value: {stats['ratios'].get('shot_accuracy')}")
    except Exception as exc:
        fail(failures, f"career shot accuracy behavior check crashed: {exc}")
    finally:
        if namespace_backup is not None:
            sys.modules["bo3tracker"] = namespace_backup
        else:
            sys.modules.pop("bo3tracker", None)


def main():
    failures = []
    test_python_syntax(failures)
    test_generated_app_javascript_parses(failures)
    test_api_circular_import_safety(failures)
    test_version_metadata(failures)
    test_core_assets(failures)
    test_xp_csv_contract(failures)
    test_camo_processor_contract(failures)
    test_best_matches_contract(failures)
    test_player_stats_backup_contract(failures)
    test_best_match_sanitizer_behavior(failures)
    test_runner_contract(failures)
    test_theme_contracts(failures)
    test_compact_mode_contract(failures)
    test_management_tools_contract(failures)
    test_app_metadata_consistency(failures)
    test_ftp_uploader_contract(failures)
    test_app_paths_contract(failures)
    test_updater_managed_paths_cover_runner_assets(failures)
    test_api_data_map_index_contract(failures)
    test_api_data_pagination_contract(failures)
    test_api_data_map_detail_weapon_merge_contract(failures)
    test_map_weapons_category_override_contract(failures)
    test_ui_main_map_detail_frontend(failures)
    test_stats_processor_weapons_priority(failures)
    test_map_challenge_ui_contract(failures)
    test_tracker_config_backup_contract(failures)
    test_workshop_images_contract(failures)
    test_global_stats_weapon_summary_contract(failures)
    test_runner_source_completeness(failures)
    test_graph_overlay_contract(failures)
    test_career_profile_recent_additions(failures)

    if failures:
        print(f"\n{len(failures)} smoke test failure(s).")
        raise SystemExit(1)

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
