#!/usr/bin/env bash
#   ⚡ THUNDER-X ⚡   natural language -> tested XPath
#
#   ./run.sh parse "<instruction>"           1. nl_parser: read one instruction
#   ./run.sh extract <url>                   2. page_extractor: list the elements of a page (file:///... works too)
#   ./run.sh find <url> "<instruction>"      1 + 2 -> 3. element_finder (rules only)
#   ./run.sh pipeline <url> "<instruction>"  the whole pipeline: 1 + 2 -> 3 -> 4. laya -> 5. xpath_builder -> 6. executor
#   ./run.sh ui                              the web UI: service on :8000 + UI on http://localhost:5173
#   ./run.sh all   (or just ./run.sh)        everything: venv, Laya, service, UI. Ctrl+C stops it all
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

# Steps 1 to 3, and 4 to 6 when the last argument is "full". Prints each step's output.
run_steps() {
  exec "$PY" -c '
import asyncio, sys
from thunderx.element_finder.services import find
from thunderx.executor.services import execute
from thunderx.laya.services import decide
from thunderx.nl_parser.services import parse
from thunderx.page_extractor import services as page_extractor
from thunderx.xpath_builder.services import build


def show(result, steps):
    for step in steps:
        print(f"   step      {step}")
    print(f"   status    {result.status.upper()}  (route: {result.route} · confidence {result.confidence:.2f})")
    if result.reason:
        print(f"   reason    {result.reason}")
    if result.element:
        e = result.element
        print(f"   element   #{e.index} <{e.tag}> {e.label}   sections={e.sections}")
    for e in result.candidates[:5]:
        print(f"   candidate #{e.index} <{e.tag}> {e.label}   sections={e.sections}")


async def main(url, instruction, mode):
    # One hidden window for the whole run: the executor runs the XPath on the same page.
    session = await page_extractor.open_session(url, headless=True)
    try:
        parsed = parse(instruction)                                 # 1. nl_parser
        page = await page_extractor.extract(session.session_id)     # 2. page_extractor
        found = find(parsed, page.elements)                         # 3. element_finder: takes 1 + 2

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
        if mode != "full":
            return

        print("4. LAYA")
        picked = await decide(found)                                # 4. laya: takes 3
        if found.status == "found":
            print("   skipped   element_finder already found it")
        else:
            show(picked, picked.steps[len(found.steps):])

        print("5. XPATH_BUILDER")
        built = build(picked)                                       # 5. xpath_builder: takes 4, no browser
        for step in built.steps[len(picked.steps):]:
            print(f"   step      {step}")
        print(built.model_dump_json(indent=2, include={"action", "xpath", "value", "confidence"}))

        print("6. EXECUTOR")
        browser = page_extractor.get_browser(session.session_id)
        result = await execute(built, picked.element, browser, "act")  # 6. executor: takes 5, runs it, does the action
        for step in result.steps[len(built.steps):]:
            print(f"   step      {step}")
        print()
        print(result.model_dump_json(indent=2, include={"action", "xpath", "value", "confidence", "status", "effect", "reason"}))
    finally:
        await page_extractor.close_session(session.session_id)


asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
' "$@"
}

cmd="${1:-all}"; shift || true
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
    run_steps "$url" "$*" rules
    ;;
  pipeline)
    [[ $# -gt 1 ]] || die 'usage: ./run.sh pipeline <url> "<instruction>"'
    ensure_venv
    ensure_laya
    url="$1"; shift
    say "opening $url in a hidden browser..."
    run_steps "$url" "$*" full
    ;;
  ui|all)
    banner
    say "1/4 python environment"
    ensure_venv
    say "2/4 Laya model"
    ensure_laya
    say "3/4 UI packages"
    command -v npm >/dev/null || die "npm not found (install Node.js)"
    [[ -d frontend/node_modules ]] || (cd frontend && npm install --silent)
    say "4/4 service + UI"
    "$PY" -m uvicorn thunderx.main:app --port 8000 &
    service_pid=$!
    trap 'kill $service_pid 2>/dev/null' EXIT
    echo
    ok "UI       -> ${cyan}http://localhost:5173$off"
    ok "service  -> ${cyan}http://localhost:8000/docs$off"
    ok "Laya     -> ${cyan}http://localhost:8001/health$off"
    say "Ctrl+C stops the service and the UI (Laya keeps running: docker compose stop laya)"
    echo
    (cd frontend && npm run dev)
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
