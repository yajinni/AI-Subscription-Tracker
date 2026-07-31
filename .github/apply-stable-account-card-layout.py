from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one {label} match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Expected one {label} regex match, found {count}")
    return updated


app_path = Path("src/App.tsx")
app = app_path.read_text()
app = replace_once(
    app,
    'import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";',
    'import { useCallback, useEffect, useMemo, useState } from "react";',
    "React import",
)
app = replace_once(
    app,
    '  const googleUnavailableLabel = modelsOnly ? "Model connected" : waitingForMetrics ? "Waiting for metrics" : "Unavailable";\n',
    '  const googleUnavailableLabel = modelsOnly ? "Model connected" : waitingForMetrics ? "Waiting for metrics" : "Unavailable";\n'
    '  const creditLabel = account.lastUsage?.unlimitedCredits\n'
    '    ? "Credits: Unlimited"\n'
    '    : account.lastUsage?.creditsUsd != null\n'
    '      ? `Credits: $${account.lastUsage.creditsUsd.toFixed(2)}`\n'
    '      : "Credits: —";\n',
    "credit label insertion",
)
app = regex_once(
    app,
    r'  const cardRef = useRef<HTMLElement \| null>\(null\);\n.*?  const metricContentKey = windows\n    \.map\(\(window\) => \[window\.id, window\.label, window\.remainingPercent, window\.windowSeconds, window\.resetsAt\]\.join\(":"\)\)\n    \.join\("\\\|"\);\n',
    '',
    "responsive state block",
)
app = regex_once(
    app,
    r'\n  useLayoutEffect\(\(\) => \{\n    compactTriggerWidthRef\.current = null;\n.*?  \}, \[account\.email, account\.label, account\.plan, compactMetrics, metricContentKey, status\.label\]\);\n',
    '\n',
    "responsive effects",
)
app = replace_once(
    app,
    '    <article\n      ref={cardRef}\n      className={`provider-account-card ${needsAttention ? "needs-attention" : ""}${actionsOnEmail ? " account-actions-on-email" : ""}${compactMetrics ? " account-metrics-compact" : ""}`}\n    >',
    '    <article className={`provider-account-card ${needsAttention ? "needs-attention" : ""}`}>',
    "article responsive classes",
)
app = replace_once(app, '<div ref={identityRef} className="account-card-identity">', '<div className="account-card-identity">', "identity ref")
app = replace_once(app, '<div ref={nameRowRef} className="account-card-name-row">', '<div className="account-card-name-row">', "name row ref")
app = replace_once(app, '<div ref={actionsRef} className="account-card-name-actions">', '<div className="account-card-name-actions">', "actions ref")
app = regex_once(
    app,
    r'      <div ref=\{metricsRef\} className=\{`account-card-metrics \$\{windows\.length > 2 \? "multi-row-metrics" : ""\}`\}>.*?      </div>\n    </article>',
    '''      <div className={`account-card-metrics ${windows.length > 2 ? "multi-row-metrics" : ""}`}>
        {windows.length ? windows.map((window, index) => (
          <AccountUsageMetric
            key={window.id}
            window={window}
            unavailableLabel={googleUnavailableLabel}
            creditLabel={index === 0 ? creditLabel : null}
          />
        )) : (
          <div className="account-usage-metric unavailable-metric">
            <span className="metric-label">Usage</span>
            <div className="metric-value-row">
              <strong className="metric-full-value">Unavailable</strong>
              <span className="account-metric-track"><span className="tone-neutral" style={{ width: "0%" }} /></span>
              <span className="metric-inline-credit">{creditLabel}</span>
            </div>
            <span className="metric-reset">Refresh this account to retrieve its limits.</span>
          </div>
        )}
      </div>
    </article>''',
    "account metrics block",
)
app = regex_once(
    app,
    r'function AccountUsageMetric\(\{ window, unavailableLabel = "Unavailable" \}: \{ window: UsageWindow; unavailableLabel\?: string \}\) \{.*?\n\}\n\nfunction IntegrationView',
    '''function AccountUsageMetric({
  window,
  unavailableLabel = "Unavailable",
  creditLabel = null,
}: {
  window: UsageWindow;
  unavailableLabel?: string;
  creditLabel?: string | null;
}) {
  const remaining = window.remainingPercent;
  const width = remaining == null ? 0 : Math.min(100, Math.max(0, remaining));
  const tone = usageTone(remaining);
  return (
    <div className="account-usage-metric">
      <div className="metric-heading">
        <span className="metric-label">{window.label}</span>
        {windowLength(window) ? <span className="metric-window-pill">{windowLength(window)}</span> : null}
      </div>
      <div className="metric-value-row">
        <strong className="metric-full-value">{remaining == null ? unavailableLabel : `${Math.round(remaining)}% remaining`}</strong>
        <span className="account-metric-track"><span className={`tone-${tone}`} style={{ width: `${width}%` }} /></span>
        {creditLabel ? <span className="metric-inline-credit">{creditLabel}</span> : null}
      </div>
      <span className="metric-reset">{window.resetsAt ? `Resets ${formatTime(window.resetsAt)}` : remaining == null ? "This provider has not reported a quota value yet" : "Rolling window"}</span>
    </div>
  );
}

function IntegrationView''',
    "usage metric component",
)
app_path.write_text(app)

responsive = '''/* Account cards keep one stable visual structure at every width. */
.provider-account-card {
  container-name: account-card;
  container-type: inline-size;
  min-height: max-content;
}

.provider-account-card .account-card-identity {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    "name actions"
    "email empty";
  align-items: center;
  column-gap: 8px;
  min-width: 0;
}

.provider-account-card .account-card-name-row {
  grid-area: name;
  min-width: 0;
  flex-wrap: nowrap;
  overflow: hidden;
}

.provider-account-card .account-card-name-row > h2,
.provider-account-card .account-card-name-row > .account-card-name-input {
  min-width: 0;
  flex: 1 1 auto;
}

.provider-account-card .account-card-email {
  grid-area: email;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.provider-account-card .account-card-name-actions {
  grid-area: actions;
  display: inline-flex !important;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  flex: 0 0 auto;
  margin-left: auto;
  visibility: visible;
}

.provider-account-card .account-card-name-actions .account-card-action {
  display: grid !important;
  flex: 0 0 auto;
  width: 30px !important;
  height: 30px !important;
}

.provider-account-card .account-card-name-actions .account-card-action svg,
.provider-account-card .account-card-name-actions .account-card-action::before {
  width: 24px !important;
  height: 24px !important;
}

.provider-account-card .account-card-metrics.multi-row-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.provider-account-card .account-card-metrics .account-usage-metric,
.provider-account-card .account-card-metrics .account-usage-metric + .account-usage-metric {
  min-width: 0;
  height: auto;
  border-left: 0 !important;
}

@container account-card (max-width: 760px) {
  .provider-account-card-header {
    grid-template-columns: 46px minmax(0, 1fr) auto;
    gap: 12px;
    min-height: 72px;
    padding: 11px 13px;
  }

  .account-card-provider-icon {
    width: 44px;
    height: 44px;
  }

  .account-card-provider-icon svg,
  .account-card-provider-icon img {
    width: 28px;
    height: 28px;
  }

  .account-card-name-row {
    gap: 6px;
  }

  .account-card-name-row h2 {
    font-size: 16px;
    line-height: 21px;
  }

  .account-card-identity p {
    font-size: 12px;
    line-height: 16px;
  }

  .account-card-name-actions {
    gap: 2px !important;
  }

  .account-card-name-actions .account-card-action {
    width: 27px !important;
    height: 27px !important;
  }

  .account-card-name-actions .account-card-action svg,
  .account-card-name-actions .account-card-action::before {
    width: 21px !important;
    height: 21px !important;
  }

  .account-status-badge,
  .account-plan-badge {
    padding-inline: 6px;
    font-size: 9px;
  }

  .account-card-metrics {
    gap: 0 12px;
    padding-inline: 13px;
  }

  .account-usage-metric {
    padding: 12px 0;
  }

  .metric-value-row {
    grid-template-columns: auto minmax(34px, 1fr) auto;
    gap: 7px;
  }

  .metric-full-value {
    font-size: 17px !important;
    line-height: 21px !important;
  }

  .metric-inline-credit,
  .metric-window-pill,
  .metric-reset {
    font-size: 10px;
  }
}

@container account-card (max-width: 560px) {
  .provider-account-card-header {
    grid-template-columns: 40px minmax(0, 1fr) auto;
    gap: 8px;
    padding: 9px 10px;
  }

  .account-card-provider-icon {
    width: 38px;
    height: 38px;
  }

  .account-card-provider-icon svg,
  .account-card-provider-icon img {
    width: 24px;
    height: 24px;
  }

  .account-card-name-row {
    gap: 4px;
  }

  .account-card-name-row h2 {
    font-size: 14px;
    line-height: 19px;
  }

  .account-card-name-actions .account-card-action {
    width: 24px !important;
    height: 24px !important;
  }

  .account-card-name-actions .account-card-action svg,
  .account-card-name-actions .account-card-action::before {
    width: 18px !important;
    height: 18px !important;
  }

  .account-card-header-actions {
    gap: 4px;
  }

  .account-card-metrics {
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0 9px;
    padding-inline: 10px;
  }

  .account-usage-metric {
    padding: 10px 0;
  }

  .metric-heading {
    gap: 6px;
  }

  .metric-label {
    font-size: 9px;
    letter-spacing: 0.05em;
  }

  .metric-window-pill,
  .metric-inline-credit {
    padding: 1px 5px;
  }

  .metric-value-row {
    gap: 5px;
    margin-block: 7px 6px;
  }

  .metric-full-value {
    font-size: 15px !important;
    line-height: 19px !important;
  }

  .account-metric-track {
    min-width: 28px;
    height: 5px;
  }
}
'''
Path("src/account-card-responsive.css").write_text(responsive)

obsidian_path = Path("src/obsidian-dashboard.css")
obsidian = obsidian_path.read_text()
obsidian = regex_once(
    obsidian,
    r'\.account-card-metrics \{.*?\n\.unavailable-metric \{',
    '''.account-card-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 210px), 1fr));
  align-items: start;
  grid-auto-rows: max-content;
  gap: 0 18px;
  padding: 0 16px;
  overflow: visible;
}

.account-usage-metric {
  min-width: 0;
  min-height: 0;
  height: auto;
  padding: 14px 0;
}

.metric-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.metric-window-pill,
.metric-inline-credit {
  flex: 0 0 auto;
  padding: 2px 7px;
  border: 1px solid #37343b;
  border-radius: 3px;
  color: #b3acb8;
  background: #181717;
  font-size: 11px;
  white-space: nowrap;
}

.metric-value-row {
  display: grid;
  grid-template-columns: auto minmax(44px, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-width: 0;
  margin: 10px 0 8px;
}

.metric-full-value {
  display: block;
  margin: 0;
  color: #f5f1ef;
  font-size: 20px;
  line-height: 24px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.metric-inline-credit {
  overflow: hidden;
  max-width: 150px;
  text-overflow: ellipsis;
}

.account-metric-track {
  min-width: 44px;
  height: 6px;
}

.metric-reset {
  display: block;
  margin-top: 0;
  color: #a8a1ac;
  font-size: 12px;
  line-height: 16px;
}

.unavailable-metric {''',
    "metric CSS block",
)
obsidian_path.write_text(obsidian)

changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text()
changelog = replace_once(
    changelog,
    '## Unreleased\n\n_No unreleased user-facing changes yet._',
    '''## Unreleased

### Fixed

- OpenAI account cards now grow to fit all quota content instead of clipping shorter than their metrics.

### Improved

- Provider-reported credits now appear inline with the percentage and usage bar instead of occupying a separate quota tile.
- Narrow account cards preserve the same information and visual structure while progressively tightening spacing, icons, and typography instead of switching to a different compact design.''',
    "changelog Unreleased section",
)
changelog_path.write_text(changelog)
