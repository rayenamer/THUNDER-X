"""The pipeline: each part's output is the next part's input, and LogsDb records it as it goes.

    instruction ─► nl_parser ──────┐
                                   ├─► element_finder ─► laya ─► xpath_builder ─► executor
    page ───────► page_extractor ──┘
                                                                       │
                                                                       ▼
                                                     logs_db: Session ─< Prompt ─< Run ─< Step, Screenshot

Every part stays independent; only this file knows the order.
Recording never breaks a run: if LogsDb fails, the run's result is still returned.
"""

import logging
import time

from pydantic import BaseModel

from thunderx.element_finder import services as element_finder
from thunderx.element_finder.models import FindResult
from thunderx.executor import services as executor
from thunderx.executor.models import ExecutionResult, Mode
from thunderx.laya import services as laya
from thunderx.logs_db import services as logs
from thunderx.logs_db.models import now
from thunderx.nl_parser import services as nl_parser
from thunderx.nl_parser.models import ParsedInstruction
from thunderx.page_extractor import services as page_extractor
from thunderx.page_extractor.models import PageSnapshot, SessionInfo
from thunderx.xpath_builder import services as xpath_builder

logger = logging.getLogger("thunderx.pipeline")

# What LogsDb keeps of the picked element: enough to know which one it was.
ELEMENT_FIELDS = {"index", "tag", "role", "label", "text", "sections", "attributes", "xpath", "backend_node_id"}


class OpenRequest(BaseModel):
    url: str
    title: str | None = None  # the session's name, given by the user. None: the page's own title
    headless: bool = True     # hidden browser: the UI shows the page through screenshots


class RunRequest(BaseModel):
    session_id: str          # a window opened with POST /sessions
    position: int = 1        # the step's place in the session's chain: 1, 2, 3...
    instruction: str         # "Hover over ok under Employee section"
    mode: Mode = "validate"  # "act" also does the action: the next step runs on the page it leaves


class RunResponse(ExecutionResult):
    run_id: int | None = None  # where LogsDb recorded it: GET /logs/runs/{run_id}


# ── sessions ────────────────────────────────────────────────────────────────

async def open_session(url: str, title: str | None = None, headless: bool = True) -> SessionInfo:
    info = await page_extractor.open_session(url, headless=headless)
    if title:
        info.title = title  # the user's name for the session wins over the page's title
    record(logs.create_session, info.session_id, info.url, info.title)
    return info


async def close_session(session_id: str) -> None:
    await page_extractor.close_session(session_id)
    record(logs.close_session, session_id)


# ── one step ────────────────────────────────────────────────────────────────

async def run_in_session(session_id: str, position: int, instruction: str, mode: Mode = "validate") -> RunResponse:
    """On the page open in a session's window, as it is right now."""
    started_at = now()
    clock = time.monotonic()

    page = await page_extractor.extract(session_id)
    parsed = nl_parser.parse(instruction)

    found = element_finder.find(parsed, page.elements)  # rules: context resolver + direct matcher
    found = await laya.decide(found, page)               # only acts if the rules didn't find it
    built = xpath_builder.build(found)                   # writes the XPaths, no browser

    browser = page_extractor.get_browser(session_id)
    result = await executor.execute(built, found.element, browser, mode)  # runs them on the page, acts

    duration_ms = int((time.monotonic() - clock) * 1000)
    run_id = record(save_run, session_id, position, instruction, mode, page, parsed, found, result, started_at, duration_ms)
    return RunResponse(**result.model_dump(), run_id=run_id)


# ── recording ───────────────────────────────────────────────────────────────

def save_run(
    session_id: str,
    position: int,
    instruction: str,
    mode: Mode,
    page: PageSnapshot,
    parsed: ParsedInstruction,
    found: FindResult,
    result: ExecutionResult,
    started_at,
    duration_ms: int,
) -> int:
    """Record one run: its prompt (created, or updated if the text changed), the run, its steps, its screenshot."""
    if logs.get_session(session_id) is None:  # a session opened without going through open_session()
        logs.create_session(session_id, page.url, page.title)

    prompt = logs.find_prompt(session_id, position)
    if prompt is None:
        prompt = logs.create_prompt(session_id, position, instruction)
    elif prompt.instruction != instruction:
        logs.update_prompt(prompt.id, instruction=instruction)

    element = None
    if found.element is not None:
        element = found.element.model_dump(include=ELEMENT_FIELDS)

    run = logs.create_run(
        prompt.id,
        instruction=instruction,
        mode=mode,
        status=result.status,
        page_url=page.url,
        elements_on_page=len(page.elements),
        parsed=parsed.model_dump(),
        element=element,
        candidates=len(found.candidates),
        action=result.action,
        xpath=result.xpath,
        value=result.value,
        confidence=result.confidence,
        route=result.route,
        effect=result.effect,
        reason=result.reason,
        page_url_after=result.url,
        started_at=started_at,
        duration_ms=duration_ms,
    )
    logs.add_steps(run.id, result.steps)

    if result.screenshot:
        highlight = result.highlight.model_dump() if result.highlight else None
        width = int(result.highlight.viewport_width) if result.highlight else None
        height = int(result.highlight.viewport_height) if result.highlight else None
        logs.save_screenshot(run.id, result.screenshot, width, height, highlight)

    return run.id


def record(function, *args):
    """Call a LogsDb function. If it fails, log it and carry on: recording never breaks the pipeline."""
    try:
        return function(*args)
    except Exception:
        logger.exception("LogsDb couldn't record %s", function.__name__)
        return None
