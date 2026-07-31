from pathlib import Path
import json
import re

VERSION = "0.2.46"
DATE = "2026-07-31"

package = json.loads(Path("package.json").read_text())
if package.get("version") != VERSION:
    raise SystemExit(f"package.json version is {package.get('version')}, expected {VERSION}")

cargo = Path("src-tauri/Cargo.toml").read_text()
if not re.search(r'^version = "0\.2\.46"$', cargo, re.M):
    raise SystemExit("Cargo.toml version is not 0.2.46")

tauri = json.loads(Path("src-tauri/tauri.conf.json").read_text())
if tauri.get("version") != VERSION:
    raise SystemExit(f"tauri.conf.json version is {tauri.get('version')}, expected {VERSION}")

changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text()
old = """## Unreleased

### Fixed

- OpenAI account cards now grow to fit all quota content instead of clipping shorter than their metrics.

### Improved

- Provider-reported credits now appear inline with the percentage and usage bar instead of occupying a separate quota tile.
- Narrow account cards preserve the same information and visual structure while progressively tightening spacing, icons, and typography instead of switching to a different compact design.

## 0.2.45 - 2026-07-31
"""
new = f"""## Unreleased

_No unreleased user-facing changes yet._

## {VERSION} - {DATE}

### Fixed

- OpenAI account cards now grow to fit all quota content instead of clipping shorter than their metrics.

### Improved

- Provider-reported credits now appear inline with the percentage and usage bar instead of occupying a separate quota tile.
- Narrow account cards preserve the same information and visual structure while progressively tightening spacing, icons, and typography instead of switching to a different compact design.

## 0.2.45 - 2026-07-31
"""
if changelog.count(old) != 1:
    raise SystemExit(f"Expected exactly one unreleased changelog block, found {changelog.count(old)}")
changelog_path.write_text(changelog.replace(old, new, 1))

Path(".github/release-trigger").write_text(
    "Release build requested on 2026-07-31 for AI Subscription Tracker v0.2.46 with account cards that grow to fit all quota content, provider credits shown inline with percentage and usage bars, and one stable visual structure that progressively compresses at narrower widths.\n"
)
