from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} match, found {count}")
    return text.replace(old, new, 1)


app_path = Path("src/App.tsx")
app = app_path.read_text(encoding="utf-8")
app = replace_once(
    app,
    'metric.querySelectorAll<HTMLElement>(".metric-heading, .metric-full-value, .metric-reset")',
    'metric.querySelectorAll<HTMLElement>(".metric-label, .metric-window-pill, .metric-full-value, .metric-reset")',
    "metric crowding selector",
)
app_path.write_text(app, encoding="utf-8")

css_path = Path("src/account-card-responsive.css")
css = css_path.read_text(encoding="utf-8")
css = replace_once(
    css,
    '''.provider-account-card:not(.account-metrics-compact) .account-card-metrics .account-usage-metric {
  display: block !important;
}

.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-heading {
  display: grid !important;
}''',
    '''.provider-account-card:not(.account-metrics-compact) .account-card-metrics .account-usage-metric {
  display: grid !important;
}

.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-heading {
  display: contents !important;
}''',
    "detailed metric grid",
)
css = replace_once(
    css,
    '''.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-full-value,
.provider-account-card:not(.account-metrics-compact) .account-card-metrics .account-metric-track,
.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-reset {
  display: block !important;
}''',
    '''.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-full-value,
.provider-account-card:not(.account-metrics-compact) .account-card-metrics .account-metric-track {
  display: block !important;
}

.provider-account-card:not(.account-metrics-compact) .account-card-metrics .metric-reset {
  display: grid !important;
}''',
    "detailed reset grid",
)
css_path.write_text(css, encoding="utf-8")
print("Restored detailed metric grid layout")
