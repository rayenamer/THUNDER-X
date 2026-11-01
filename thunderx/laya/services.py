"""Laya: pick one element when element_finder's rules couldn't (design step 4).

Takes element_finder's result and chooses among its `candidates`:
    ambiguous   the 2+ elements the direct matcher found
    not_found   the interactive elements the context resolver kept

Laya's answer is kept only if its confidence reaches MIN_CONFIDENCE. Otherwise the step stays
"ambiguous", with Laya's top 5 as candidates (for the LLM, later).

The model runs in Docker:  ./run.sh laya up  (http://localhost:8001).
"""

import os

import httpx

from thunderx.element_finder.models import FindResult
from thunderx.laya import helpers as h

LAYA_URL = os.environ.get("LAYA_URL", "http://localhost:8001")
LAYA_API_KEY = os.environ.get("LAYA_API_KEY")
TIMEOUT_SECONDS = 10

# τ (design step 5). Placeholder until it is set from the dev set (design §3.4).
MIN_CONFIDENCE = 0.3
TOP_FOR_LLM = 5


async def decide(finder_result: FindResult) -> FindResult:
    """Let Laya choose among element_finder's candidates. Never raises: if Laya is down, the input comes back."""
    if finder_result.status == "found":
        return finder_result

    parsed = finder_result.parsed
    steps = list(finder_result.steps)

    if not finder_result.candidates:
        steps.append("laya: skipped, nothing to choose from")
        return finder_result.model_copy(update={"steps": steps})

    candidates = h.shortlist(parsed.raw, finder_result.candidates)
    steps.append(f"laya: {len(candidates)} candidates")
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
    request = h.build_request(parsed.raw, operation, candidates)
    try:
        response = await ask_laya(request)
        answer = response["answers"][h.question_name(operation)]
    except (httpx.HTTPError, KeyError, ValueError) as error:
        steps.append(f"laya: no answer ({type(error).__name__}: {error})")
        return finder_result.model_copy(update={"steps": steps})

    by_id = {}
    for element in candidates:
        by_id[h.option_id(element)] = element

    choice = answer.get("choice")
    chosen = by_id.get(choice)
    if chosen is None:
        steps.append(f"laya: answered an unknown option ({choice})")
        return finder_result.model_copy(update={"steps": steps})

    probabilities = answer.get("probabilities", {})
    confidence = answer.get("answer_confidence", probabilities.get(choice, 0.0))
    ranked = sorted(candidates, key=lambda element: -probabilities.get(h.option_id(element), 0.0))
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
