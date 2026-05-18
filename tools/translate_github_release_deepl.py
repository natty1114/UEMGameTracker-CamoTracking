"""Translate a GitHub release body with DeepL and update the release.

This is intended for GitHub Actions. It reads the release from the event file,
generates localized changelog blocks, and PATCHes the release body through the
GitHub API. Translations are cached in translation_cache/ by release tag and
English body hash.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from translate_changelog_deepl import (
    DEFAULT_LANGUAGES,
    DEEPL_TARGETS,
    build_release_body,
    load_json,
    save_json,
    sha256_text,
    translate_with_deepl,
)


def github_request(url: str, token: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "BO3Tracker-ChangelogTranslator/1.0",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def release_from_event() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is not set.")
    event = load_json(Path(event_path))
    release = event.get("release")
    return release if isinstance(release, dict) else {}


def release_from_tag(repo: str, token: str, tag: str) -> dict:
    if not tag:
        return {}
    candidates = []
    raw = tag.strip()
    for candidate in (
        raw,
        raw[:1].lower() + raw[1:],
        raw[:1].upper() + raw[1:],
        raw.lstrip("vV"),
        "v" + raw.lstrip("vV"),
        "V" + raw.lstrip("vV"),
    ):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    last_error = None
    for candidate in candidates:
        url = f"https://api.github.com/repos/{repo}/releases/tags/{candidate}"
        try:
            release = github_request(url, token)
            print(f"Found release tag: {candidate}")
            return release
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code != 404:
                raise
    if last_error:
        print(
            "Could not find a release for tag variants: " + ", ".join(candidates),
            file=sys.stderr,
        )
    return {}


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    api_key = os.environ.get("DEEPL_API_KEY", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    tag = os.environ.get("RELEASE_TAG", "").strip()
    force = os.environ.get("FORCE_TRANSLATE", "").strip().lower() in {"1", "true", "yes"}

    if not token:
        print("GITHUB_TOKEN is not set.", file=sys.stderr)
        return 2
    if not api_key:
        print("DEEPL_API_KEY is not set.", file=sys.stderr)
        return 2
    if not repo:
        print("GITHUB_REPOSITORY is not set.", file=sys.stderr)
        return 2

    release = release_from_tag(repo, token, tag) if tag else release_from_event()
    if not release:
        print("No release was found in the event or release tag lookup.", file=sys.stderr)
        return 2

    release_id = release.get("id")
    source_text = str(release.get("body") or "").strip()
    release_tag = str(release.get("tag_name") or tag or release_id or "release").strip()
    if not release_id:
        print("Release is missing an id.", file=sys.stderr)
        return 2
    if not source_text:
        print("Release body is empty; nothing to translate.")
        return 0
    if "<!-- changelog:" in source_text and not force:
        print("Release already contains changelog language blocks; skipping. Run with force=true to rebuild them.")
        return 0

    languages = DEFAULT_LANGUAGES
    source_hash = sha256_text(source_text)
    cache_path = Path("translation_cache") / f"github_release_{release_tag}.json"
    cache = load_json(cache_path)
    translations = cache.get("translations") if cache.get("source_hash") == source_hash else {}
    if not isinstance(translations, dict):
        translations = {}

    for language in languages:
        if translations.get(language) and not force:
            continue
        print(f"Translating {release_tag} to {language}...")
        translations[language] = translate_with_deepl(source_text, DEEPL_TARGETS[language], api_key)

    save_json(
        cache_path,
        {
            "release_tag": release_tag,
            "source_hash": source_hash,
            "translations": translations,
        },
    )

    body = build_release_body(source_text, translations, languages)
    update_url = f"https://api.github.com/repos/{repo}/releases/{release_id}"
    github_request(update_url, token, method="PATCH", payload={"body": body})
    print(f"Updated release {release_tag} with localized changelog blocks.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        raise
