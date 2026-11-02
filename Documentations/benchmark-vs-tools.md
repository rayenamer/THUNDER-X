# Thunder-X vs available tools

Same job for everyone: **a web page + a sentence → the element to act on.**
Only Thunder-X does it with just the URL and the sentence, and gives back a tested XPath.

---

## 1. What each tool needs, what it gives back

| | Thunder-X | Stagehand `observe()` | browser-use `get_element_by_prompt()` | MindAct | UGround / ShowUI (vision) |
|---|---|---|---|---|---|
| **Input** | URL + instruction | a page you open and drive + instruction | a browser session you open + prompt | the page's HTML + a task | a screenshot + instruction |
| **LLM needed** | **no** | yes | yes | no (its own small models) | it *is* a 2–3B vision model |
| **API key / cost per step** | **none** | yes (or a local model you host) | yes (or a local model you host) | none | none |
| **Hardware** | **CPU** | the LLM's | the LLM's | CPU | GPU recommended (CPU: tens of seconds per step) |
| **Output** | **XPath + action + value + confidence** | XPath + action | an element (no XPath) | an element choice | a pixel (x, y) |
| **XPath style** | **stable first** (id, label, text in section…), position last | position (`/html/body/div[2]/…`) | – | – | – |
| **XPath tested on the page** | **yes**: 1 match, the right element | no | – | – | – |
| **Can say "not here"** | **yes** (`not_found`) | partly | partly | no | no: always gives a point |
| **Same answer every time** | **yes** for rules | no (LLM sampling) | no (LLM sampling) | yes | yes |
| **Explains itself** | **yes**: route + every step logged | short description | no | no | no |
| **Page data leaves the machine** | **no** | yes, if cloud LLM | yes, if cloud LLM | no | no |

---

## 2. Why it matters for test automation

- **Only a URL and a sentence.** The others need a page already opened and driven by your code, an HTML dump, or a screenshot pipeline.
- **No LLM on easy steps.** Most actions (e.g., "Click Login") are handled by a lightweight rule-based module in milliseconds. A small local model (laya-browser, 322M, CPU) is only invoked when the module cannot confidently determine the action.
- **A tested XPath, not a guess.** The XPath is run on the live page before it's returned: exactly one match, and it's the element that was picked.
- **Stable XPaths.** `//*[@id='username']` survives a redesign; `/html/body/div[2]/form/input[1]` doesn't.
- **"Not found" is an answer.** A wrong answer becomes a silent bad test; "not found" goes back to the user, who fixes it in seconds.
- **Repeatable.** Same page + same sentence → same XPath. A test suite can't depend on sampling.
- **Private and free.** Nothing is sent to a cloud LLM, no cost per step.

---

## 3. How the benchmark is run

- **Data:** The right element is picked first and the instruction written after, so the answer is known by construction.
- **Runner:** `labs/kpi_lab.ipynb`. Each row goes to the tool. The answer is **right** when it points to exactly one element and that element is the expected one. The XPath text is never compared: two different XPaths can point to the same element.

---

## 4. Results

*(to fill after the runs)*

| | Thunder-X | Stagehand | browser-use | MindAct | UGround-2B |
|---|---|---|---|---|---|
| accuracy (right / all) | | | | | |
| precision (right / answered) | | | | | |
| coverage (answered / all) | | | | | |
| action accuracy | | | | | – |
| time per step (median) | | | | | |
| cost per 1,000 steps | 0 | | | 0 | 0 |
| XPath still right after a small page change | | | – | – | – |

Per category (unique, duplicate_text, label_assoc, icon_only…) and per action: see `kpi_lab.ipynb`.

---

## 5. Generalist LLMs (GPT, Claude, Gemini)

An LLM can't open a URL, whatever its size: it only reads the text it's given. To do this job it needs a system around it that opens the page, renders it, cleans the HTML, fits it in its context, and checks its answer. Thunder-X *is* that system, without the LLM.

suppose we did this benchmark

| | Thunder-X | gpt-5-mini | gpt-5 | claude-haiku-5-5 | claude-sonnet-5-5 | gemini-2.5-flash | gemini-2.5-pro |
|---|---|---|---|---|---|---|---|
| accuracy | | | | | | | |
| precision | | | | | | | |
| median time | | | | | | | |
| tokens per row | 0 | | | | | | |

**What this compares: Laya  and some componentsagainst LLMs.** Thunder-X answers most steps with rules and calls Laya only when they can't decide; Laya is one part of the system, and its share shows in the per-route breakdown (`direct_matcher` vs `laya`). The question is whether a purpose-built system beats sending the page to a large LLM, on accuracy, time, cost and repeatability.

---

## 6. Honest limits

- The benchmark rows are built from public practice pages (the-internet, demoqa, selenium web form…): simpler than a real customer app.
- Instructions come from templates, with values in quotes: easier to parse than what real users write.
- The builder uses Thunder-X's `page_extractor` to list elements: an element it misses can't become a test case.
- Vision models are scored on the element only: they don't produce an XPath at all.
