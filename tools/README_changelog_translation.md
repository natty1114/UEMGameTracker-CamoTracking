# Changelog Translation

This repo includes a small DeepL helper for generating GitHub release notes with language blocks that BO3 Tracker can switch between automatically.

## One-time setup

Set your DeepL key as a Windows environment variable. Do not commit it to the repo.

```powershell
setx DEEPL_API_KEY "your-new-deepl-key"
```

Restart PowerShell/GitHub Desktop after setting it.

## Generate translated release notes

```powershell
python tools/translate_changelog_deepl.py CHANGELOG_4.6.2.md
```

Or use the PowerShell helper:

```powershell
.\tools\translate_changelog_deepl.ps1 CHANGELOG_4.6.2.md
```

This writes:

- `CHANGELOG_4.6.2.release.md`
- `translation_cache/CHANGELOG_4.6.2.json`

The cache stores translations by a hash of the English changelog. If the English text has not changed, the script reuses the cached translations and does not spend DeepL characters again.

Paste the contents of the `.release.md` file into the GitHub release body.

## GitHub Actions

For GitHub automation, add a repository secret named `DEEPL_API_KEY`.

The workflow at `.github/workflows/translate-release-changelog.yml` runs when a GitHub release is published. It reads the English release body, translates it with DeepL, caches the translations, and updates the release body with `<!-- changelog:xx -->` blocks.

English stays visible on the GitHub release page. Extra languages are placed inside collapsible `<details>` sections so visitors do not have to scroll through every translation to reach the release assets.

You can also run it manually from GitHub Actions with a release tag such as `v4.6.2`.
