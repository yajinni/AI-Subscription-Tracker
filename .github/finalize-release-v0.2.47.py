from pathlib import Path

path = Path('CHANGELOG.md')
text = path.read_text()
old = '''## Unreleased

### Fixed

- Credits are no longer shown on Google Antigravity or OpenCode Go accounts, which do not report a credit balance.
- OpenAI usage-window badges now stay in the same top-row position used by other providers.

### Improved

- Usage percentages now omit the redundant word **remaining**.
- Narrower account cards retain the exact same content, element positions, icon sizes, and typography; only flexible widths such as account names and usage bars contract.
'''
new = '''## Unreleased

_No unreleased user-facing changes yet._

## 0.2.47 - 2026-07-31

### Fixed

- Credits are no longer shown on Google Antigravity or OpenCode Go accounts, which do not report a credit balance.
- OpenAI usage-window badges now stay in the same top-row position used by other providers.

### Improved

- Usage percentages now omit the redundant word **remaining**.
- Narrower account cards retain the exact same content, element positions, icon sizes, and typography; only flexible widths such as account names and usage bars contract.
'''
if old not in text:
    raise SystemExit('Expected Unreleased v0.2.47 notes were not found')
path.write_text(text.replace(old, new, 1))
