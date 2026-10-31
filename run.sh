#!/usr/bin/env bash
#   ⚡ THUNDER-X ⚡   natural language -> tested XPath
#
#   ./run.sh                      start the service (same as: serve)
#   ./run.sh serve [port]         start the API with auto-reload (default 8000)
#   ./run.sh parse "<prompt>"     run nl_parser on one instruction
#   ./run.sh try "<prompt>"       same, but through the running service
#   ./run.sh extract <url>        list the elements page_extractor sees (file:///... works too)
#   ./run.sh find <url> "<prompt>" find the element an instruction points at, on that page
#   ./run.sh setup                (re)create the venv and install deps
set -euo pipefail
cd "$(dirname "$0")"

VENV=.venv
PY="$VENV/bin/python"
PORT_DEFAULT=8000

yellow=$'\e[33m'; cyan=$'\e[36m'; green=$'\e[32m'; red=$'\e[31m'; dim=$'\e[2m'; off=$'\e[0m'

banner() {
  printf '%s' "$yellow"
  cat <<'EOF'
   _____ _                     _                 __  __
  |_   _| |__  _   _ _ __   __| | ___ _ __       \ \/ /
    | | | '_ \| | | | '_ \ / _` |/ _ \ '__|  ⚡   \  /
    | | | | | | |_| | | | | (_| |  __/ |         /  \
    |_| |_| |_|\__,_|_| |_|\__,_|\___|_|        /_/\_\
EOF
  printf '%s  %s\n\n' "$off$dim" "natural language -> tested XPath$off"
}

say()  { printf '%s⚡%s %s\n' "$cyan" "$off" "$*"; }
ok()   { printf '%s✔%s %s\n' "$green" "$off" "$*"; }
die()  { printf '%s✘%s %s\n' "$red" "$off" "$*" >&2; exit 1; }

setup() {
  command -v python3 >/dev/null || die "python3 not found"
  say "creating $VENV"
  python3 -m venv "$VENV"
  say "installing thunderx"
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet -e .
  touch "$VENV/.installed"
  ok "ready"
}

ensure_venv() {
  [[ -f "$VENV/.installed" && "$VENV/.installed" -nt pyproject.toml ]] || setup
}

cmd="${1:-serve}"; shift || true
case "$cmd" in
  serve)
    ensure_venv; banner
    port="${1:-$PORT_DEFAULT}"
    say "docs  -> ${cyan}http://localhost:$port/docs$off"
    say "parse -> POST http://localhost:$port/nl-parser/parse"
    exec "$PY" -m uvicorn thunderx.main:app --reload --port "$port"
    ;;
  parse)
    [[ $# -gt 0 ]] || die 'usage: ./run.sh parse "<instruction>"'
    ensure_venv
    exec "$PY" -c 'import sys; from thunderx.nl_parser.services import parse
print(parse(sys.argv[1]).model_dump_json(indent=2))' "$*"
    ;;
  try)
    [[ $# -gt 0 ]] || die 'usage: ./run.sh try "<instruction>"'
    ensure_venv
    port="${PORT:-$PORT_DEFAULT}"
    body=$("$PY" -c 'import json,sys; print(json.dumps({"instruction": sys.argv[1]}))' "$*")
    curl -fsS -X POST "http://localhost:$port/nl-parser/parse" -H 'content-type: application/json' -d "$body" \
      | "$PY" -m json.tool --no-ensure-ascii \
      || die "service not reachable on :$port (start it with ./run.sh serve)"
    ;;
  extract)
    [[ $# -gt 0 ]] || die 'usage: ./run.sh extract <url>'
    ensure_venv
    say "opening $1 in a hidden browser..."
    exec "$PY" -c '
import asyncio, sys
from thunderx.page_extractor.services import extract_once

page = asyncio.run(extract_once(sys.argv[1]))
print(f"\n{page.title}  ({page.url})  {len(page.elements)} elements\n")
header = "{:>4}  {:<8} {:<12} {:<40}  {:<40} {}".format("#", "TAG", "ROLE", "LABEL", "SECTIONS", "FLAGS")
print(header)
print("-" * len(header))
for e in page.elements:
    role = e.role or ""
    label = (e.label or "")[:40]
    where = (" > ".join(e.sections) or "-")[:40]
    flags = ("click " if e.interactive else "      ") + ("" if e.visible else "hidden")
    print(f"{e.index:>4}  {e.tag:<8} {role:<12} {label:<40}  {where:<40} {flags}")
' "$1"
    ;;
  find)
    [[ $# -gt 1 ]] || die 'usage: ./run.sh find <url> "<instruction>"'
    ensure_venv
    url="$1"; shift
    say "opening $url in a hidden browser..."
    exec "$PY" -c '
import asyncio, sys
from thunderx.element_finder.services import find
from thunderx.nl_parser.services import parse
from thunderx.page_extractor.services import extract_once

url, instruction = sys.argv[1], sys.argv[2]

# 1. nl_parser: the instruction -> action, target, hint
parsed = parse(instruction)

# 2. page_extractor: the page -> its elements
page = asyncio.run(extract_once(url))

# 3. element_finder: both outputs -> one element
result = find(parsed, page.elements)

hint = "-"
if parsed.hint:
    hint = " ".join(part for part in [parsed.hint.relation, parsed.hint.text, parsed.hint.role] if part)

print()
print("1. NL_PARSER")
print(f"   action={parsed.action} · text={parsed.target.text} · role={parsed.target.role} · ordinal={parsed.target.ordinal} · hint={hint} · value={parsed.value}")
print("2. PAGE_EXTRACTOR")
print(f"   {page.title} ({page.url}) · {len(page.elements)} elements")
print("3. ELEMENT_FINDER")
for step in result.steps:
    print(f"   step      {step}")
print(f"   status    {result.status.upper()}  (route: {result.route})")
if result.reason:
    print(f"   reason    {result.reason}")
if result.element:
    e = result.element
    print(f"   element   #{e.index} <{e.tag}> {e.label}   sections={e.sections}")
    print(f"   xpath     {e.xpath}   (browser-use position xpath, xpath_builder comes next)")
for e in result.candidates[:10]:
    print(f"   candidate #{e.index} <{e.tag}> {e.label}   sections={e.sections}")
' "$url" "$*"
    ;;
  setup)
    setup
    ;;
  help|-h|--help)
    banner; sed -n '4,10p' "$0" | sed 's/^#//'
    ;;
  *)
    die "unknown command '$cmd' (try ./run.sh help)"
    ;;
esac
