"""Data classes of LogsDb: everything Thunder-X does, recorded (SQLite for now).

    Session ──< Prompt ──< Run ──< Step
                            │
                            └── Screenshot (0 or 1)

    Session     one browser window
    Prompt      one node of the chain: an instruction at a position (1, 2, 3...)
    Run         one execution of a prompt (Run all, Run this step, after an edit...): input, output, timing
    Step        one line of the run's timeline: which part did what (design §4: find which box failed)
    Screenshot  the page after the run, as JPEG bytes. Its own table: listing runs never loads images.

Each table only points to its direct parent. Each class is both a Pydantic model and a SQLite table (SQLModel).
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


class Session(SQLModel, table=True):
    id: str = Field(primary_key=True)          # the same id as page_extractor's session
    start_url: str                             # where Run all starts from
    title: str | None = None
    opened_at: datetime = Field(default_factory=now)
    closed_at: datetime | None = None


class Prompt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    position: int                              # its place in the chain: 1, 2, 3...
    instruction: str                           # the current text ("hover on Privacy in the footer")
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Run(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt.id", index=True)

    # ── input ──
    instruction: str                           # the exact text that ran (the prompt may be edited later)
    mode: str                                  # "validate" or "act"
    page_url: str | None = None                # the page it ran on
    elements_on_page: int | None = None        # how many elements page_extractor listed
    parsed: dict | None = Field(default=None, sa_column=Column(JSON))   # nl_parser's output

    # ── what was picked ──
    element: dict | None = Field(default=None, sa_column=Column(JSON))  # the picked element: tag, label, sections, attributes...
    candidates: int | None = None              # how many elements were left to choose from

    # ── output (the executor's result) ──
    status: str                                # verified / no_change / failed / not_found
    action: str | None = None
    xpath: str | None = None
    value: str | None = None
    confidence: float = 0.0
    route: str | None = None                   # which part picked: "direct_matcher", "laya"
    effect: str | None = None                  # act mode: "went to https://..."
    reason: str | None = None                  # why it failed / wasn't found
    page_url_after: str | None = None

    # ── timing ──
    started_at: datetime = Field(default_factory=now)
    duration_ms: int | None = None


class Step(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id", index=True)
    position: int                              # order in the timeline: 1, 2, 3...
    part: str                                  # "context", "direct matcher", "laya", "xpath builder", "executor"
    message: str                               # "aria-label ✔ 1 match, the right one"
    ok: bool | None = None                     # ✔ True, ✘ False, neither None


class Screenshot(SQLModel, table=True):
    run_id: int = Field(foreign_key="run.id", primary_key=True)  # one screenshot per run at most
    image: bytes                               # the JPEG itself (BLOB), ~50-150 KB
    width: int | None = None                   # the visible page's size when it was taken
    height: int | None = None
    highlight: dict | None = Field(default=None, sa_column=Column(JSON))  # the element's box on it, if any


# ── history: what the endpoints send back (not tables) ──────────────────────

class RunHistory(SQLModel):
    run: Run
    steps: list[Step]
    has_screenshot: bool          # the image itself: GET /logs/runs/{id}/screenshot
    highlight: dict | None = None  # the element's box on that screenshot


class PromptHistory(SQLModel):
    prompt: Prompt
    runs: list[RunHistory]  # newest first


class SessionHistory(SQLModel):
    session: Session
    prompts: list[PromptHistory]  # in chain order
