from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one {label} match, found {count}")
    return text.replace(old, new, 1)


app_path = Path("src/App.tsx")
app = app_path.read_text()
status_line = '            <span className={`account-status-badge ${status.className}`}>{status.label}</span>'
actions = "\n".join([
    '            <div className="account-card-name-actions">',
    '              <button',
    '                type="button"',
    '                className="account-card-action"',
    '                title="Usage notifications"',
    '                aria-label={`Configure usage notifications for ${account.label}`}',
    '                disabled={Boolean(busy)}',
    '                onClick={onNotifications}',
    '              ><BellIcon /></button>',
    '              <button',
    '                type="button"',
    '                className="account-card-action remove-action"',
    '                title="Remove this account"',
    '                aria-label={`Remove ${account.label}`}',
    '                disabled={Boolean(busy)}',
    '                onClick={onRemove}',
    '              >{isRemoving ? <span className="mini-spinner" /> : <CloseIcon />}</button>',
    '              <button',
    '                type="button"',
    '                className={`account-card-action ${isRefreshing ? "spinning" : ""}`}',
    '                title="Refresh this account"',
    '                aria-label={`Refresh ${account.label}`}',
    '                disabled={Boolean(busy)}',
    '                onClick={onRefresh}',
    '              ><RefreshIcon /></button>',
    '            </div>',
])
app = replace_once(app, status_line, status_line + "\n" + actions, "account status line")

marker = '<div className="account-card-header-actions">'
start = app.index(marker)
end = app.index('\n        </div>', start)
segment = app[start:end]
for title in ("Refresh this account", "Remove this account", "Usage notifications"):
    title_pos = segment.index(f'title="{title}"')
    button_start = segment.rfind('          <button', 0, title_pos)
    button_end = segment.index('</button>', title_pos) + len('</button>')
    segment = segment[:button_start] + segment[button_end:]
segment = replace_once(
    segment,
    marker,
    '<div className={`account-card-header-actions ${account.provider === "google_ai_studio" ? "has-google-action" : "plan-only-actions"}`}>',
    "header action container",
)
app = app[:start] + segment + app[end:]
app = replace_once(
    app,
    '<div className="account-card-metrics">',
    '<div className={`account-card-metrics ${windows.length > 2 ? "multi-row-metrics" : ""}`}>',
    "metric container",
)
app = replace_once(
    app,
    '      <strong>{remaining == null ? unavailableLabel : `${Math.round(remaining)}% remaining`}</strong>',
    '      <strong className="metric-full-value">{remaining == null ? unavailableLabel : `${Math.round(remaining)}% remaining`}</strong>\n      <span className="metric-compact-value">{remaining == null ? unavailableLabel : `${Math.round(remaining)}%`}</span>',
    "metric value",
)
app_path.write_text(app)

css_path = Path("src/ui-refinements.css")
css = css_path.read_text()
css_marker = "/* Compact account cards and Trello-style reorder support */"
if css_marker in css:
    raise SystemExit("Compact card CSS already exists")
css += r'''

/* Compact account cards and Trello-style reorder support */
.account-card-name-row > h2,
.account-card-name-row > .account-card-name-input,
.account-card-name-row > .account-name-edit,
.account-card-name-row > .account-status-badge {
  order: 1;
}

.account-card-name-row > h2,
.account-card-name-row > .account-card-name-input {
  min-width: 0;
  flex: 1 1 auto;
}

.account-card-name-row::after {
  order: 2;
  flex: 0 0 auto;
}

.account-card-name-actions {
  order: 3;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  margin-left: auto;
}

.account-card-header-actions.plan-only-actions {
  display: none;
}

.metric-compact-value {
  display: none;
}

.account-card-metrics.multi-row-metrics {
  grid-template-columns: repeat(2, minmax(210px, 1fr));
  column-gap: 28px;
}

.account-card-metrics.multi-row-metrics .account-usage-metric,
.account-card-metrics.multi-row-metrics .account-usage-metric + .account-usage-metric {
  padding-left: 0;
  padding-right: 0;
  border-left: 0;
}

@media (max-width: 1180px) {
  .provider-account-card-header {
    grid-template-columns: 46px minmax(0, 1fr) auto;
    align-items: center;
    gap: 12px;
    min-height: 72px;
    padding: 12px 14px;
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

  .account-card-name-actions {
    gap: 2px;
  }

  .account-card-action {
    width: 28px !important;
    height: 28px !important;
  }

  .provider-account-card .account-card-name-actions .account-card-action svg,
  .provider-account-card .account-card-name-actions .account-card-action::before {
    width: 22px !important;
    height: 22px !important;
  }

  .account-card-header-actions.has-google-action {
    grid-column: 2 / -1;
    justify-content: flex-start;
    padding-top: 4px;
    border-top: 0;
  }

  .account-card-metrics,
  .account-card-metrics.multi-row-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0 18px;
    padding: 0 14px;
  }

  .account-card-metrics .account-usage-metric,
  .account-card-metrics .account-usage-metric + .account-usage-metric {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
    min-height: 48px;
    padding: 10px 0;
    border: 0;
  }

  .account-card-metrics .metric-heading {
    display: contents;
  }

  .account-card-metrics .metric-label,
  .account-card-metrics .metric-full-value,
  .account-card-metrics .account-metric-track,
  .account-card-metrics .metric-reset {
    display: none !important;
  }

  .account-card-metrics .metric-compact-value {
    order: 1;
    display: inline;
    color: #f5f1ef;
    font-size: 15px;
    line-height: 20px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .account-card-metrics .metric-window-pill {
    order: 2;
    display: inline-flex;
    grid-column: auto;
    grid-row: auto;
    align-self: center;
    width: fit-content;
    margin: 0;
    padding: 2px 7px;
    white-space: nowrap;
  }

  .account-card-metrics .account-credit-metric {
    display: none !important;
  }
}
'''
css_path.write_text(css)

reorder_path = Path("src/dashboard-reorder.ts")
reorder = reorder_path.read_text()
reorder = replace_once(
    reorder,
    "  lastClientX: number;\n  lastClientY: number;\n  descriptor: DragDescriptor;",
    "  lastClientX: number;\n  lastClientY: number;\n  grabOffsetY: number;\n  sourceHeight: number;\n  descriptor: DragDescriptor;",
    "active drag fields",
)
reorder = replace_once(
    reorder,
    "function updatePlaceholderFromPointer(drag: ActiveDrag, clientY: number): void {\n  const elements = reorderElements(drag);",
    "function floatingCenterY(drag: ActiveDrag): number {\n  return drag.lastClientY - drag.grabOffsetY + drag.sourceHeight / 2;\n}\n\nfunction updatePlaceholderFromPointer(drag: ActiveDrag): void {\n  const clientY = floatingCenterY(drag);\n  const elements = reorderElements(drag);",
    "placeholder function",
)
reorder = replace_once(
    reorder,
    "    lastClientX: event.clientX,\n    lastClientY: event.clientY,\n    descriptor,",
    "    lastClientX: event.clientX,\n    lastClientY: event.clientY,\n    grabOffsetY: candidate.startY - bounds.top,\n    sourceHeight: bounds.height,\n    descriptor,",
    "active drag construction",
)
reorder = replace_once(reorder, '    transform: "translate3d(0, 0, 0)",', '    transform: "translate3d(0, 0, 0) rotate(0.8deg) scale(1.01)",', "initial transform")
reorder = replace_once(reorder, "  updatePlaceholderFromPointer(active, event.clientY);", "  updatePlaceholderFromPointer(active);", "initial placeholder call")
reorder = replace_once(reorder, "      updatePlaceholderFromPointer(drag, drag.lastClientY);", "      updatePlaceholderFromPointer(drag);", "scroll placeholder call")
reorder = replace_once(reorder, "  updatePlaceholderFromPointer(drag, event.clientY);", "  updatePlaceholderFromPointer(drag);", "pointer placeholder call")
reorder = replace_once(
    reorder,
    '  drag.source.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 0)`;',
    '  drag.source.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 0) rotate(0.8deg) scale(1.01)`;',
    "floating transform",
)
reorder_path.write_text(reorder)

reorder_css_path = Path("src/dashboard-reorder.css")
reorder_css = reorder_css_path.read_text()
reorder_css = replace_once(
    reorder_css,
    "  border: 1px dashed rgba(208, 188, 255, 0.72);\n  background: rgba(160, 120, 255, 0.1);\n  box-shadow: inset 3px 0 0 rgba(160, 120, 255, 0.72);",
    "  border: 0;\n  background: transparent;\n  box-shadow: none;",
    "placeholder styling",
)
reorder_css_path.write_text(reorder_css)

changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text()
changelog = replace_once(
    changelog,
    "## Unreleased\n\n_No unreleased user-facing changes yet._",
    "## Unreleased\n\n### Improved\n\n- Compact account cards now keep notification, remove, and refresh controls beside the account name and use the lower row for concise percentage and usage-window summaries.\n- Provider and account dragging now follows the Trello-style interaction reference: the floating card tracks the pointer while a transparent full-size gap moves through the list and neighboring items animate into the exact pending order.\n\n### Fixed\n\n- Accounts with multiple rows of usage limits no longer indent later rows with a misplaced vertical separator.",
    "Unreleased changelog",
)
changelog_path.write_text(changelog)
