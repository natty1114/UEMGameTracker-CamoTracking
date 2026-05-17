import ast
import csv
import json
import tempfile
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
    "bo3tracker.py",
    "camo_processor.py",
    "challenge_system.py",
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
    "dev_tools/modules/remote_management_manifest.py",
    "dev_tools/modules/validation.py",
]

EXCLUDED_RELEASE_PY_FILES = {
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


def test_theme_contracts(failures):
    game_data_text = read_text("game_data.py")
    overlay_text = read_text("overlay_themes.py")
    ui_text = read_text("ui_main.py")

    for theme in ["Clouds", "Dog Pack", "DeadOps Arcade", "Pacific Paradise", "Shi No Numa"]:
        if theme in game_data_text:
            ok(f"game_data.py marks always-available theme: {theme}")
        else:
            fail(failures, f"game_data.py missing always-available theme: {theme}")

    for theme in ["Clouds", "Dog Pack", "Shi No Numa"]:
        if f'"{theme}"' in overlay_text or f"'{theme}'" in overlay_text:
            ok(f"overlay_themes.py includes overlay palette: {theme}")
        else:
            fail(failures, f"overlay_themes.py missing overlay palette: {theme}")

        if f'"{theme}"' in ui_text or f"'{theme}'" in ui_text or f"{theme}:" in ui_text:
            ok(f"ui_main.py includes graph/settings theme support: {theme}")
        else:
            fail(failures, f"ui_main.py missing graph/settings theme support: {theme}")


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

    challenge_manager_text = read_text("challenge_system.py")
    if "apply_remote_manifest" in challenge_manager_text:
        ok("challenge_system.py can apply remote manifests")
    else:
        fail(failures, "challenge_system.py missing remote manifest apply hook")

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

    for filename in ["config.json", "best_matches.json", "challenges.json", "map_challenges.json", "map_index_cache.json", "map_detail_summary.json"]:
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


def test_ui_main_map_detail_frontend(failures):
    ui_text = read_text("ui_main.py")
    for required in [
        "async function loadMoreMapMatches",
        "map-detail-load-more-btn",
        "async function refreshMapSelection",
        "async function openMapSelectionPage",
        "async function openMapDetail",
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
    for required in [
        "renderOperationsChallenges",
        "isMapChallenge",
        "normalizeWorkshopLink",
        "map-challenge-section",
        "map-challenge-heading",
        "map-challenge-heading-link",
    ]:
        if required in ui_text or required in css_text:
            ok(f"map challenge UI includes: {required}")
        else:
            fail(failures, f"map challenge UI missing: {required}")


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


def main():
    failures = []
    test_python_syntax(failures)
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
    test_management_tools_contract(failures)
    test_app_metadata_consistency(failures)
    test_ftp_uploader_contract(failures)
    test_app_paths_contract(failures)
    test_updater_managed_paths_cover_runner_assets(failures)
    test_api_data_map_index_contract(failures)
    test_api_data_pagination_contract(failures)
    test_ui_main_map_detail_frontend(failures)
    test_stats_processor_weapons_priority(failures)
    test_map_challenge_ui_contract(failures)
    test_workshop_images_contract(failures)
    test_global_stats_weapon_summary_contract(failures)
    test_runner_source_completeness(failures)
    test_graph_overlay_contract(failures)

    if failures:
        print(f"\n{len(failures)} smoke test failure(s).")
        raise SystemExit(1)

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
