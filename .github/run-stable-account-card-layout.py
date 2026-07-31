from pathlib import Path

script_path = Path(".github/apply-stable-account-card-layout.py")
script = script_path.read_text()
start = script.index("app = regex_once(\n    app,\n    r'  const cardRef")
end = script.index("app = regex_once(\n    app,\n    r'\\n  useLayoutEffect", start)
replacement = '''app = regex_once(
    app,
    r'  const cardRef = useRef<HTMLElement \\| null>\\(null\\);\\n.*?  const metricContentKey = windows\\n.*?    \\.join\\("\\|"\\);\\n',
    '',
    "responsive state block",
)
'''
fixed = script[:start] + replacement + script[end:]
exec(compile(fixed, str(script_path), "exec"))
