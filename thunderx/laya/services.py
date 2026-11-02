"""Laya: pick one element when element_finder's rules couldn't (design step 4).

Takes element_finder's result and chooses among its `candidates`:
    ambiguous   the 2+ elements the direct matcher found
    not_found   the interactive elements the context resolver kept

Laya's answer is kept only if its confidence reaches MIN_CONFIDENCE. Otherwise the step stays
"ambiguous", with Laya's top 5 as candidates (for the LLM, later).

Two models to choose from, with LAYA_MODEL (run.sh passes it on):
    browser (default)   cklxx/laya-browser                Docker service "laya-browser", http://localhost:8002
    mind2web            Quantum08/laya-browser-mind2web   Docker service "laya",         http://localhost:8001
"""

import os

import httpx

from thunderx.element_finder.models import FindResult
from thunderx.laya import helpers as h
from thunderx.page_extractor.models import PageSnapshot

LAYA_MODEL = os.environ.get("LAYA_MODEL", "browser")
LAYA_URLS = {"mind2web": "http://localhost:8001", "browser": "http://localhost:8002"}
LAYA_URL = os.environ.get("LAYA_URL", LAYA_URLS.get(LAYA_MODEL, LAYA_URLS["mind2web"]))
SHORTLIST_SIZE = h.BROWSER_SHORTLIST_SIZE if LAYA_MODEL == "browser" else h.SHORTLIST_SIZE
LAYA_API_KEY = os.environ.get("LAYA_API_KEY")
TIMEOUT_SECONDS = 10

# τ (design step 5). Placeholder until it is set from the dev set (design §3.4).
MIN_CONFIDENCE = 0.3
TOP_FOR_LLM = 5


async def decide(finder_result: FindResult, page: PageSnapshot | None = None) -> FindResult:
    """Let Laya choose among element_finder's candidates. Never raises: if Laya is down, the input comes back.

    page: the page the candidates come from. Only cklxx/laya-browser reads it (url, title, first 1200
    characters of text), because it was trained with it; the Mind2Web Laya wasn't, and doesn't get it.
    """
    if finder_result.status == "found":
        return finder_result

    parsed = finder_result.parsed
    steps = list(finder_result.steps)

    if not finder_result.candidates:
        steps.append("laya: skipped, nothing to choose from")
        return finder_result.model_copy(update={"steps": steps})

    candidates = h.shortlist(parsed.raw, finder_result.candidates, size=SHORTLIST_SIZE)
    steps.append(f"laya ({LAYA_MODEL}): {len(candidates)} candidates")
    if len(candidates) == 1:
        # One option is no choice: a softmax over one option always says 1.0
        return finder_result.model_copy(update={
            "status": "ambiguous",
            "candidates": candidates,
            "route": "laya",
            "reason": "only one candidate left, Laya can't compare it to anything",
            "steps": steps,
        })

    operation = h.operation_of(parsed.action)
    request, by_id = h.build_request(parsed.raw, operation, candidates, LAYA_MODEL, page)
    try:
        response = await ask_laya(request)
        answer = response["answers"][h.question_name(operation)]
    except (httpx.HTTPError, KeyError, ValueError) as error:
        steps.append(f"laya: no answer ({type(error).__name__}: {error})")
        return finder_result.model_copy(update={"steps": steps})

    choice = answer.get("choice")
    chosen = by_id.get(choice)
    if chosen is None:
        steps.append(f"laya: answered an unknown option ({choice})")
        return finder_result.model_copy(update={"steps": steps})

    probabilities = answer.get("probabilities", {})
    confidence = answer.get("answer_confidence", probabilities.get(choice, 0.0))
    best_first = sorted(by_id, key=lambda option: -probabilities.get(option, 0.0))
    ranked = [by_id[option] for option in best_first]
    steps.append(f"laya: picked {h.render_option(chosen)} · confidence {confidence:.2f}")

    if confidence >= MIN_CONFIDENCE:
        return FindResult(
            status="found",
            element=chosen,
            candidates=ranked,  # runners-up, best first: the executor tries the next one if this fails
            confidence=confidence,
            route="laya",
            steps=steps,
            parsed=parsed,
        )
    return FindResult(
        status="ambiguous",
        candidates=ranked[:TOP_FOR_LLM],
        confidence=confidence,
        route="laya",
        reason=f"Laya isn't sure: {confidence:.2f} < {MIN_CONFIDENCE}",
        steps=steps,
        parsed=parsed,
    )


async def ask_laya(request: dict) -> dict:
    headers = {}
    if LAYA_API_KEY:
        headers["Authorization"] = f"Bearer {LAYA_API_KEY}"

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.post(f"{LAYA_URL}/v1/systemone", json=request, headers=headers)
        response.raise_for_status()
        return response.json()
