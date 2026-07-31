from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


app_path = Path("src/App.tsx")
app = app_path.read_text(encoding="utf-8")

app = replace_once(
    app,
    'import { useCallback, useEffect, useMemo, useState } from "react";',
    'import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";',
    "React hooks import",
)

app = replace_once(
    app,
    '''function windowLength(window: UsageWindow): string | null {
  if (!window.windowSeconds) return null;
  const hours = Math.round(window.windowSeconds / 3600);
  if (hours >= 24 && hours % 24 === 0) return `${hours / 24}d window`;
  return `${hours}h window`;
}''',
    '''function windowLength(window: UsageWindow): string | null {
  const id = window.id.toLowerCase().replaceAll("-", "_");
  const label = window.label.toLowerCase();
  if (id.includes("monthly") || label.includes("monthly")) return "Monthly";
  if (!window.windowSeconds) return null;
  const hours = Math.round(window.windowSeconds / 3600);
  if (hours >= 24 && hours % 24 === 0) return `${hours / 24}d window`;
  return `${hours}h window`;
}''',
    "window length helper",
)

app = replace_once(
    app,
    '''  const googleUnavailableLabel = modelsOnly ? "Model connected" : waitingForMetrics ? "Waiting for metrics" : "Unavailable";

  useEffect(() => {
    if (!editing) setLabel(account.label);
  }, [account.label, editing]);

  const commitRename = async () => {''',
    '''  const googleUnavailableLabel = modelsOnly ? "Model connected" : waitingForMetrics ? "Waiting for metrics" : "Unavailable";
  const cardRef = useRef<HTMLElement | null>(null);
  const identityRef = useRef<HTMLDivElement | null>(null);
  const nameRowRef = useRef<HTMLDivElement | null>(null);
  const actionsRef = useRef<HTMLDivElement | null>(null);
  const metricsRef = useRef<HTMLDivElement | null>(null);
  const compactTriggerWidthRef = useRef<number | null>(null);
  const [actionsOnEmail, setActionsOnEmail] = useState(false);
  const [compactMetrics, setCompactMetrics] = useState(false);
  const metricContentKey = windows
    .map((window) => [window.id, window.label, window.remainingPercent, window.windowSeconds, window.resetsAt].join(":"))
    .join("|");

  useEffect(() => {
    if (!editing) setLabel(account.label);
  }, [account.label, editing]);

  useLayoutEffect(() => {
    compactTriggerWidthRef.current = null;
    setCompactMetrics(false);
  }, [metricContentKey]);

  useLayoutEffect(() => {
    const card = cardRef.current;
    const identity = identityRef.current;
    const nameRow = nameRowRef.current;
    const actions = actionsRef.current;
    const metrics = metricsRef.current;
    if (!card || !identity || !nameRow || !actions || !metrics) return;

    let frame = 0;
    const numericStyle = (value: string): number => {
      const parsed = Number.parseFloat(value);
      return Number.isFinite(parsed) ? parsed : 0;
    };
    const intrinsicWidth = (element: HTMLElement): number => {
      const style = window.getComputedStyle(element);
      return Math.ceil(
        Math.max(element.scrollWidth, element.getBoundingClientRect().width)
          + numericStyle(style.marginLeft)
          + numericStyle(style.marginRight),
      );
    };

    const measure = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        const nameChildren = Array.from(nameRow.children).filter(
          (child): child is HTMLElement => child instanceof HTMLElement,
        );
        const nameStyle = window.getComputedStyle(nameRow);
        const nameGap = numericStyle(nameStyle.columnGap || nameStyle.gap);
        let nameRequired = nameChildren.reduce((sum, child) => sum + intrinsicWidth(child), 0)
          + Math.max(0, nameChildren.length - 1) * nameGap;
        const generatedPlan = window.getComputedStyle(nameRow, "::after");
        if (generatedPlan.content && generatedPlan.content !== "none" && generatedPlan.content !== '""') {
          nameRequired += numericStyle(generatedPlan.width) + numericStyle(generatedPlan.marginLeft);
        }
        const identityGap = numericStyle(window.getComputedStyle(identity).columnGap);
        const shouldMoveActions = nameRequired + intrinsicWidth(actions) + identityGap > identity.clientWidth + 1;
        setActionsOnEmail((current) => current === shouldMoveActions ? current : shouldMoveActions);

        const cardWidth = card.clientWidth;
        if (!compactMetrics) {
          const detailedOverflow = metrics.scrollWidth > metrics.clientWidth + 1
            || Array.from(metrics.querySelectorAll<HTMLElement>(".account-usage-metric")).some((metric) => {
              if (metric.scrollWidth > metric.clientWidth + 1) return true;
              return Array.from(metric.querySelectorAll<HTMLElement>(".metric-heading, .metric-full-value, .metric-reset"))
                .some((element) => element.scrollWidth > element.clientWidth + 1);
            });
          if (detailedOverflow) {
            compactTriggerWidthRef.current = cardWidth;
            setCompactMetrics(true);
          }
        } else {
          const trigger = compactTriggerWidthRef.current;
          if (trigger != null && cardWidth > trigger + 24) {
            setCompactMetrics(false);
          }
        }
      });
    };

    const observer = new ResizeObserver(measure);
    observer.observe(card);
    observer.observe(identity);
    observer.observe(metrics);
    measure();
    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frame);
    };
  }, [account.email, account.label, account.plan, compactMetrics, metricContentKey, status.label]);

  const commitRename = async () => {''',
    "responsive measurement hooks",
)

app = replace_once(
    app,
    '''    <article className={`provider-account-card ${needsAttention ? "needs-attention" : ""}`}>
      <header className="provider-account-card-header">''',
    '''    <article
      ref={cardRef}
      className={`provider-account-card ${needsAttention ? "needs-attention" : ""}${actionsOnEmail ? " account-actions-on-email" : ""}${compactMetrics ? " account-metrics-compact" : ""}`}
    >
      <header className="provider-account-card-header">''',
    "account article",
)

identity_start = app.index('        <div className="account-card-identity">')
identity_end_marker = '        <div className={`account-card-header-actions ${account.provider === "google_ai_studio" ? "has-google-action" : "plan-only-actions"}`}>'
identity_end = app.index(identity_end_marker, identity_start)
new_identity = '''        <div ref={identityRef} className="account-card-identity">
          <div ref={nameRowRef} className="account-card-name-row">
            {editing ? (
              <input
                className="account-card-name-input"
                value={label}
                maxLength={80}
                disabled={isRenaming}
                autoFocus
                aria-label={`Rename ${account.label}`}
                onChange={(event) => {
                  setLabel(event.target.value);
                  setRenameError(null);
                }}
                onBlur={() => void commitRename()}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    event.currentTarget.blur();
                  } else if (event.key === "Escape") {
                    event.preventDefault();
                    setLabel(account.label);
                    setRenameError(null);
                    setEditing(false);
                  }
                }}
              />
            ) : <h2>{account.label}</h2>}
            {!editing ? (
              <button type="button" className="account-name-edit" title="Edit account name" aria-label={`Edit ${account.label}`} onClick={() => setEditing(true)}>
                <EditIcon />
              </button>
            ) : null}
            <span className={`account-status-badge ${status.className}`}>{status.label}</span>
          </div>
          <p className="account-card-email">{account.email ?? providerName(account.provider)}</p>
          <div ref={actionsRef} className="account-card-name-actions">
            <button
              type="button"
              className="account-card-action"
              title="Usage notifications"
              aria-label={`Configure usage notifications for ${account.label}`}
              disabled={Boolean(busy)}
              onClick={onNotifications}
            ><BellIcon /></button>
            <button
              type="button"
              className="account-card-action remove-action"
              title="Remove this account"
              aria-label={`Remove ${account.label}`}
              disabled={Boolean(busy)}
              onClick={onRemove}
            >{isRemoving ? <span className="mini-spinner" /> : <CloseIcon />}</button>
            <button
              type="button"
              className={`account-card-action ${isRefreshing ? "spinning" : ""}`}
              title="Refresh this account"
              aria-label={`Refresh ${account.label}`}
              disabled={Boolean(busy)}
              onClick={onRefresh}
            ><RefreshIcon /></button>
          </div>
          {renameError ? <small className="account-card-inline-error">{renameError}</small> : null}
        </div>
'''
app = app[:identity_start] + new_identity + app[identity_end:]

app = replace_once(
    app,
    '''      <div className={`account-card-metrics ${windows.length > 2 ? "multi-row-metrics" : ""}`}>''',
    '''      <div ref={metricsRef} className={`account-card-metrics ${windows.length > 2 ? "multi-row-metrics" : ""}`}>''',
    "metrics ref",
)

app_path.write_text(app, encoding="utf-8")

css_path = Path("src/account-card-responsive.css")
css_path.write_text('''/* Account-card responsive behavior follows real content pressure, not the app window. */
.provider-account-card {
  container-name: account-card;
  container-type: inline-size;
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
  overflow: visible;
}

.provider-account-card .account-card-name-row > h2,
.provider-account-card .account-card-name-row > .account-card-name-input {
  min-width: 0;
  flex: 1 1 auto;
}

.provider-account-card .account-card-name-row[data-plan]::after {
  max-width: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

.provider-account-card .account-card-email {
  grid-area: email;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Reserve the controls, then move them beside the email only when measured content would crowd the title row. */
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

.provider-account-card.account-actions-on-email .account-card-identity {
  grid-template-areas:
    "name name"
    "email actions";
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

/* Multi-row usage grids may shrink until their real text begins to overflow. */
.provider-account-card .account-card-metrics.multi-row-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.provider-account-card .account-card-metrics.multi-row-metrics .account-usage-metric,
.provider-account-card .account-card-metrics.multi-row-metrics .account-usage-metric + .account-usage-metric {
  min-width: 0;
  padding-left: 0;
  padding-right: 0;
  border-left: 0 !important;
}

/* Override the older viewport media rule unless measured overflow has selected compact mode. */
.provider-account-card:not(.account-metrics-compact) .account-card-metrics .account-usage-metric {
  display: block !important;
}

.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-heading {
  display: grid !important;
}

.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-label,
.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-window-pill {
  display: inline-flex !important;
}

.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-full-value,
.provider-account-card:not(.account-metrics-compact) .account-card-metrics .account-metric-track,
.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-reset {
  display: block !important;
}

.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-compact-value {
  display: none !important;
}

.provider-account-card.account-actions-on-email .provider-account-card-header,
.provider-account-card.account-metrics-compact .provider-account-card-header {
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 72px;
  padding: 12px 14px;
}

.provider-account-card.account-actions-on-email .account-card-provider-icon,
.provider-account-card.account-metrics-compact .account-card-provider-icon {
  width: 44px;
  height: 44px;
}

.provider-account-card.account-actions-on-email .account-card-provider-icon svg,
.provider-account-card.account-actions-on-email .account-card-provider-icon img,
.provider-account-card.account-metrics-compact .account-card-provider-icon svg,
.provider-account-card.account-metrics-compact .account-card-provider-icon img {
  width: 28px;
  height: 28px;
}

.provider-account-card.account-actions-on-email .account-card-name-row,
.provider-account-card.account-metrics-compact .account-card-name-row {
  gap: 6px;
}

.provider-account-card.account-actions-on-email .account-card-name-actions,
.provider-account-card.account-metrics-compact .account-card-name-actions {
  gap: 2px;
}

.provider-account-card.account-actions-on-email .account-card-action,
.provider-account-card.account-metrics-compact .account-card-action {
  width: 28px !important;
  height: 28px !important;
}

.provider-account-card.account-actions-on-email .account-card-action svg,
.provider-account-card.account-actions-on-email .account-card-action::before,
.provider-account-card.account-metrics-compact .account-card-action svg,
.provider-account-card.account-metrics-compact .account-card-action::before {
  width: 22px !important;
  height: 22px !important;
}

.provider-account-card.account-metrics-compact .account-card-header-actions.has-google-action {
  grid-column: 2 / -1;
  justify-content: flex-start;
  padding-top: 4px;
  border-top: 0;
}

.provider-account-card.account-metrics-compact .account-card-metrics,
.provider-account-card.account-metrics-compact .account-card-metrics.multi-row-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 18px;
  padding: 0 14px;
}

.provider-account-card.account-metrics-compact .account-card-metrics .account-usage-metric,
.provider-account-card.account-metrics-compact .account-card-metrics .account-usage-metric + .account-usage-metric {
  display: flex !important;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-height: 48px;
  padding: 10px 0;
  border: 0 !important;
}

.provider-account-card.account-metrics-compact .account-card-metrics .metric-heading {
  display: contents !important;
}

.provider-account-card.account-metrics-compact .account-card-metrics .metric-label,
.provider-account-card.account-metrics-compact .account-card-metrics .metric-full-value,
.provider-account-card.account-metrics-compact .account-card-metrics .account-metric-track,
.provider-account-card.account-metrics-compact .account-card-metrics .metric-reset {
  display: none !important;
}

.provider-account-card.account-metrics-compact .account-card-metrics .metric-compact-value {
  order: 1;
  display: inline !important;
  color: #f5f1ef;
  font-size: 15px;
  line-height: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.provider-account-card.account-metrics-compact .account-card-metrics .metric-window-pill {
  order: 2;
  display: inline-flex !important;
  grid-column: auto;
  grid-row: auto;
  align-self: center;
  width: fit-content;
  margin: 0;
  padding: 2px 7px;
  white-space: nowrap;
}

.provider-account-card.account-metrics-compact .account-card-metrics .account-credit-metric {
  display: none !important;
}

@container account-card (max-width: 360px) {
  .provider-account-card.account-metrics-compact .account-card-metrics,
  .provider-account-card.account-metrics-compact .account-card-metrics.multi-row-metrics {
    grid-template-columns: 1fr;
  }
}
''', encoding="utf-8")

changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text(encoding="utf-8")
changelog = replace_once(
    changelog,
    '''## Unreleased

_No unreleased user-facing changes yet._''',
    '''## Unreleased

### Improved

- OpenCode Go's monthly quota now shows a **Monthly** usage-window badge alongside its percentage.
- Account-card notification, remove, and refresh controls move beside the email only when the title row would otherwise become crowded.
- Detailed account usage remains visible while the card can still contain its real text; compact percentages activate only after measured content overflow instead of at a fixed card width.''',
    "Unreleased changelog",
)
changelog_path.write_text(changelog, encoding="utf-8")

print("Applied content-driven account-card layout patch")
