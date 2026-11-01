#!/usr/bin/env bash
#   ⚡ THUNDER-X ⚡   natural language -> tested XPath
#
#   ./run.sh parse "<instruction>"           1. nl_parser: read one instruction
#   ./run.sh extract <url>                   2. page_extractor: list the elements of a page (file:///... works too)
#   ./run.sh find <url> "<instruction>"      1 + 2 -> 3. element_finder (rules only)
#   ./run.sh pipeline <url> "<instruction>"  the whole pipeline: 1 + 2 -> 3 -> 4. laya (starts Laya in Docker)
#   ./run.sh setup                           (re)create the venv and install deps
set -euo pipefail
cd "$(dirname "$0")"

VENV=.venv
PY="$VENV/bin/python"
LAYA_HEALTH="http://localhost:8001/health"

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

ensure_laya() {
  if curl -fs "$LAYA_HEALTH" >/dev/null 2>&1; then
    return
  fi
  command -v docker >/dev/null || { say "docker not found: running without Laya"; return; }
  say "starting Laya in Docker (first time: builds the image and downloads the model, a few minutes)"
  docker compose up -d --build laya
  for _ in $(seq 120); do
    curl -fs "$LAYA_HEALTH" >/dev/null 2>&1 && { ok "Laya ready"; return; }
    sleep 3
  done
  say "Laya not ready yet (./run.sh pipeline will still run, step 4 will say so). Logs: docker compose logs -f laya"
}

# Steps 1 to 3, and 4 when the last argument is "with-laya". Prints each step's output.
run_steps() {
  exec "$PY" -c '
import asyncio, sys
from thunderx.element_finder.services import find
from thunderx.laya.services import decide
from thunderx.nl_parser.services import parse
from thunderx.page_extractor.services import extract_once


def show(result, steps):
    for step in steps:
        print(f"   step      {step}")
    print(f"   status    {result.status.upper()}  (route: {result.route} · confidence {result.confidence:.2f})")
    if result.reason:
        print(f"   reason    {result.reason}")
    if result.element:
        e = result.element
        print(f"   element   #{e.index} <{e.tag}> {e.label}   sections={e.sections}")
        print(f"   xpath     {e.xpath}   (browser-use position xpath, xpath_builder comes next)")
    for e in result.candidates[:5]:
        print(f"   candidate #{e.index} <{e.tag}> {e.label}   sections={e.sections}")


url, instruction, mode = sys.argv[1], sys.argv[2], sys.argv[3]

parsed = parse(instruction)                     # 1. nl_parser
page = asyncio.run(extract_once(url))           # 2. page_extractor
found = find(parsed, page.elements)             # 3. element_finder: takes 1 + 2

hint = "-"
if parsed.hint:
    hint = " ".join(part for part in [parsed.hint.relation, parsed.hint.text, parsed.hint.role] if part)

print()
print("1. NL_PARSER")
print(f"   action={parsed.action} · text={parsed.target.text} · role={parsed.target.role} · ordinal={parsed.target.ordinal} · hint={hint} · value={parsed.value}")
print("2. PAGE_EXTRACTOR")
print(f"   {page.title} ({page.url}) · {len(page.elements)} elements")
print("3. ELEMENT_FINDER")
show(found, found.steps)

if mode == "with-laya":
    print("4. LAYA")
    if found.status == "found":
        print("   skipped   element_finder already found it")
    else:
        final = asyncio.run(decide(found))      # 4. laya: takes 3
        show(final, final.steps[len(found.steps):])
' "$@"
}

cmd="${1:-help}"; shift || true
case "$cmd" in
  parse)
    [[ $# -gt 0 ]] || die 'usage: ./run.sh parse "<instruction>"'
    ensure_venv
    exec "$PY" -c 'import sys; from thunderx.nl_parser.services import parse
print(parse(sys.argv[1]).model_dump_json(indent=2))' "$*"
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
    run_steps "$url" "$*" rules-only
    ;;
  pipeline)
    [[ $# -gt 1 ]] || die 'usage: ./run.sh pipeline <url> "<instruction>"'
    ensure_venv
    ensure_laya
    url="$1"; shift
    say "opening $url in a hidden browser..."
    run_steps "$url" "$*" with-laya
    ;;
  setup)
    setup
    ;;
  help|-h|--help)
    banner; sed -n '4,8p' "$0" | sed 's/^#//'
    ;;
  *)
    die "unknown command '$cmd' (try ./run.sh help)"
    ;;
esac
