"""Generate localized GitHub changelog blocks with DeepL.

Usage:
    python tools/translate_changelog_deepl.py CHANGELOG_4.6.2.md

The DeepL key is read from the DEEPL_API_KEY environment variable. Translations
are cached by source-text hash so unchanged changelogs are not translated again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_LANGUAGES = ["de", "es", "fr", "it", "pt", "pl", "ru", "ja", "ko", "zh"]
DEEPL_TARGETS = {
    "de": "DE",
    "es": "ES",
    "fr": "FR",
    "it": "IT",
    "pt": "PT-PT",
    "pl": "PL",
    "ru": "RU",
    "ja": "JA",
    "ko": "KO",
    "zh": "ZH",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def deepl_endpoint(api_key: str) -> str:
    host = "api-free.deepl.com" if api_key.endswith(":fx") else "api.deepl.com"
    return f"https://{host}/v2/translate"


def translate_with_deepl(text: str, target_lang: str, api_key: str) -> str:
    body = urllib.parse.urlencode(
        {
            "text": text,
            "source_lang": "EN",
            "target_lang": target_lang,
            "preserve_formatting": "1",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        deepl_endpoint(api_key),
        data=body,
        headers={
            "Authorization": f"DeepL-Auth-Key {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "BO3Tracker-ChangelogTranslator/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    translations = payload.get("translations") or []
    if not translations or not isinstance(translations[0], dict):
        raise RuntimeError("DeepL returned no translation text.")
    return str(translations[0].get("text") or "").strip()


def changelog_block(language: str, text: str) -> str:
    return "\n".join(
        [
            f"<!-- changelog:{language} -->",
            text.strip(),
            f"<!-- /changelog:{language} -->",
        ]
    )


def language_label(language: str) -> str:
    return {
        "de": "German",
        "es": "Spanish",
        "fr": "French",
        "it": "Italiano",
        "pt": "Portuguese",
        "pl": "Polish",
        "ru": "Russian",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
    }.get(language, language)


def build_release_body(source_text: str, translations: dict[str, str], languages: list[str]) -> str:
    blocks = [changelog_block("en", source_text)]
    for language in languages:
        text = translations.get(language, "").strip()
        if text:
            blocks.append(
                "\n".join(
                    [
                        f"<details><summary>{language_label(language)} changelog</summary>",
                        "",
                        changelog_block(language, text),
                        "",
                        "</details>",
                    ]
                )
            )
    return "\n\n".join(blocks) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate a BO3 Tracker changelog into GitHub release blocks.")
    parser.add_argument("changelog", help="English changelog markdown file, e.g. CHANGELOG_4.6.2.md")
    parser.add_argument("--output", help="Output release markdown path. Default: <input>.release.md")
    parser.add_argument("--cache-dir", default="translation_cache", help="Directory for cached translations.")
    parser.add_argument("--languages", default=",".join(DEFAULT_LANGUAGES), help="Comma-separated app language codes.")
    parser.add_argument("--force", action="store_true", help="Re-translate even when cached translations exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.changelog)
    if not source_path.exists():
        print(f"Changelog not found: {source_path}", file=sys.stderr)
        return 2

    languages = [item.strip().lower() for item in args.languages.split(",") if item.strip()]
    unsupported = [language for language in languages if language not in DEEPL_TARGETS]
    if unsupported:
        print(f"Unsupported language code(s): {', '.join(unsupported)}", file=sys.stderr)
        return 2

    source_text = source_path.read_text(encoding="utf-8").strip()
    source_hash = sha256_text(source_text)
    cache_path = Path(args.cache_dir) / f"{source_path.stem}.json"
    cache = load_json(cache_path)
    translations = cache.get("translations") if cache.get("source_hash") == source_hash else {}
    if not isinstance(translations, dict):
        translations = {}

    missing = [language for language in languages if args.force or not translations.get(language)]
    if missing:
        api_key = os.environ.get("DEEPL_API_KEY", "").strip()
        if not api_key:
            print(
                "DEEPL_API_KEY is not set, and cached translations are missing for: "
                + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        for language in missing:
            print(f"Translating {language}...")
            translations[language] = translate_with_deepl(source_text, DEEPL_TARGETS[language], api_key)

    save_json(
        cache_path,
        {
            "source_file": str(source_path),
            "source_hash": source_hash,
            "translations": {language: translations[language] for language in languages if translations.get(language)},
        },
    )

    output_path = Path(args.output) if args.output else source_path.with_suffix(".release.md")
    output_path.write_text(build_release_body(source_text, translations, languages), encoding="utf-8")
    print(f"Wrote {output_path}")
    print(f"Cache: {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
