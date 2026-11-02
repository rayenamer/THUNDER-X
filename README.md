<div align="center">

# THUNDER-X 
**An open-source natural-language-to-XPath engine that doesn't rely on external LLM APIs.**
**A URL and a sentence in => a verified, actionable XPath out.**
**No LLM API. No cloud dependency. Just describe what you want**
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![browser-use](https://img.shields.io/badge/browser--use-0.13-111111)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
[![Laya](https://img.shields.io/badge/Laya-System%201%20model%20%C2%B7%20laya--browser%20322M-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co/cklxx/laya-browser)
![License](https://img.shields.io/badge/license-TBD-lightgrey)

</div>

---

## Features

- **URL + sentence** — `"Hover over 'ok' under the Employee section"` → the element, its action and value.
- **Rules first** — parser, context resolver and direct matcher answer most steps with no model at all.
- **A small model only when needed** — [laya-browser](https://huggingface.co/cklxx/laya-browser) (322M, CPU) decides when the rules find 0 or 2+ elements.
- **Verified, never guessed** — every XPath is run on the live page: exactly one match, the element that was picked.
- **Stable XPaths** — id, test id, label, text in section first; position only as a last resort.
- **Act and prove it** — click, hover, type, select, check; then the effect is checked and a screenshot taken.
- **Everything logged** — each run, each step, each screenshot, in SQLite.

## Quick start

**Requires:** Python 3.11+, Node.js + npm, Chrome or Chromium, curl · Docker ( without it, no Laya).

```bash
git clone <this repo> && cd Thunder-X
./run.sh
```

The first run creates the Python environment, installs the UI, builds the Laya image and downloads the model (a few minutes). Then open **http://localhost:5173**. `Ctrl+C` stops the service and the UI; Laya keeps running in Docker.

## Usage

```bash
./run.sh                        # everything, with laya-browser (default)
LAYA_MODEL=mind2web ./run.sh    # with the Mind2Web Laya instead
docker compose stop laya-browser
```

Without the UI:

```bash
curl -s localhost:8000/sessions -H 'content-type: application/json' \
     -d '{"url": "https://app.example.com/login"}'

curl -s localhost:8000/run -H 'content-type: application/json' \
     -d '{"session_id": "<id>", "instruction": "Type jane into the Username field", "mode": "validate"}'
```

`mode`: `validate` checks the XPath only; `act` also does the action, and the next step runs on the page it leaves.

## Project structure

```text
thunderx/
├── nl_parser/        sentence → action · target · value · hint (rules)
├── page_extractor/   the page as a list of elements (browser-use)
├── element_finder/   context resolver + direct matcher (rules)
├── laya/             request to laya-browser, in its training format
├── xpath_builder/    candidate XPaths, most stable first
├── executor/         validate · act · check · screenshot
├── logs_db/          SQLite: sessions, runs, steps, screenshots
├── pipeline.py       the only place that knows the order
└── main.py           FastAPI app
frontend/             React UI (Vite)
docker/               Laya images
labs/                 benchmark builder + KPI lab (./labs/lab.sh)
Documentations/       design, evaluation, vision
```

## Documentation

The full story (architecture as it evolved, evaluation, benchmark, vision): **[Documentations/summary.md](Documentations/summary.md)**

## License

Copyright 2026 Rayen Ameur.

This project is licensed under the Apache License 2.0. You may use, modify, and distribute this software, including for commercial purposes, subject to the terms of the license.

See the [LICENSE](LICENSE) file for details.
