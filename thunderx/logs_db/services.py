"""Core logic of LogsDb: the local database, and every function to add, read, change and delete its rows.

    Session ──< Prompt ──< Run ──< Step
                            └── Screenshot

The database is one SQLite file: data/logs.db at the repo root (git-ignored).
Change it with the THUNDERX_LOGS_DB environment variable.

    init_db()                                        once, when the service starts
    session = create_session("a1b2c3d4", "https://app.example.com")
    prompt = create_prompt(session.id, position=1, instruction="click on About us")
    run = create_run(prompt.id, instruction="click on About us", mode="act", status="verified", ...)
    add_steps(run.id, ["direct matcher: 1 match -> <a>About us</a>", ...])
    save_screenshot(run.id, base64_jpeg)

Deleting a row deletes everything under it (a session takes its prompts, their runs, steps, screenshots).
"""

import base64
import os
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session as DbSession
from sqlmodel import SQLModel, create_engine, select

from thunderx.logs_db.models import (
    Prompt,
    PromptHistory,
    Run,
    RunHistory,
    Screenshot,
    Session,
    SessionHistory,
    Step,
    now,
)

# ── the database ────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("THUNDERX_LOGS_DB", REPO_ROOT / "data" / "logs.db"))

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},  # FastAPI may use it from several threads
)


@event.listens_for(engine, "connect")
def enforce_foreign_keys(connection, _record) -> None:
    """SQLite ignores foreign keys unless asked: a run can't point to a prompt that doesn't exist."""
    connection.execute("PRAGMA foreign_keys = ON")


def init_db() -> None:
    """Create the data folder, the database file and its tables, if they don't exist yet."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def open_db() -> DbSession:
    """A connection to the database. Rows read through it stay usable after it closes."""
    return DbSession(engine, expire_on_commit=False)


# ── sessions ────────────────────────────────────────────────────────────────

def create_session(session_id: str, start_url: str, title: str | None = None) -> Session:
    return add(Session(id=session_id, start_url=start_url, title=title))


def get_session(session_id: str) -> Session | None:
    with open_db() as db:
        return db.get(Session, session_id)


def list_sessions() -> list[Session]:
    """Newest first."""
    with open_db() as db:
        return list(db.exec(select(Session).order_by(Session.opened_at.desc())))


def update_session(session_id: str, **changes) -> Session | None:
    """update_session("a1b2c3d4", title="Airbnb") -> the updated session, None if there's no such session."""
    return update(Session, session_id, changes)


def close_session(session_id: str) -> Session | None:
    """Mark the session's browser window as closed (the session and its history stay)."""
    return update(Session, session_id, {"closed_at": now()})


def close_open_sessions() -> int:
    """Mark every session still open as closed. At startup: their windows died with the previous service.

    Returns how many were closed.
    """
    with open_db() as db:
        still_open = list(db.exec(select(Session).where(Session.closed_at == None)))  # noqa: E711 (SQL "IS NULL")
        for session in still_open:
            session.closed_at = now()
            db.add(session)
        db.commit()
        return len(still_open)


def delete_session(session_id: str) -> bool:
    """Delete the session and everything under it. False if there was no such session."""
    with open_db() as db:
        session = db.get(Session, session_id)
        if session is None:
            return False
        for prompt in list(db.exec(select(Prompt).where(Prompt.session_id == session_id))):
            delete_prompt_rows(db, prompt)
        db.delete(session)
        db.commit()
        return True


# ── prompts ─────────────────────────────────────────────────────────────────

def create_prompt(session_id: str, position: int, instruction: str) -> Prompt:
    return add(Prompt(session_id=session_id, position=position, instruction=instruction))


def get_prompt(prompt_id: int) -> Prompt | None:
    with open_db() as db:
        return db.get(Prompt, prompt_id)


def find_prompt(session_id: str, position: int) -> Prompt | None:
    """The prompt at this place in the session's chain, if there is one."""
    with open_db() as db:
        query = select(Prompt).where(Prompt.session_id == session_id, Prompt.position == position)
        return db.exec(query).first()


def list_prompts(session_id: str) -> list[Prompt]:
    """The session's chain, in order: 1, 2, 3..."""
    with open_db() as db:
        query = select(Prompt).where(Prompt.session_id == session_id).order_by(Prompt.position)
        return list(db.exec(query))


def update_prompt(prompt_id: int, **changes) -> Prompt | None:
    """update_prompt(7, instruction="hover on Privacy") -> the updated prompt, None if there's no such prompt."""
    changes["updated_at"] = now()
    return update(Prompt, prompt_id, changes)


def delete_prompt(prompt_id: int) -> bool:
    """Delete the prompt and its runs. False if there was no such prompt."""
    with open_db() as db:
        prompt = db.get(Prompt, prompt_id)
        if prompt is None:
            return False
        delete_prompt_rows(db, prompt)
        db.commit()
        return True


# ── runs ────────────────────────────────────────────────────────────────────

def create_run(prompt_id: int, instruction: str, mode: str, status: str, **fields) -> Run:
    """create_run(7, "click on About us", "act", "verified", xpath="//a[...]", confidence=1.0, ...)"""
    return add(Run(prompt_id=prompt_id, instruction=instruction, mode=mode, status=status, **fields))


def get_run(run_id: int) -> Run | None:
    with open_db() as db:
        return db.get(Run, run_id)


def list_runs(prompt_id: int) -> list[Run]:
    """All the runs of one prompt, newest first."""
    with open_db() as db:
        query = select(Run).where(Run.prompt_id == prompt_id).order_by(Run.started_at.desc())
        return list(db.exec(query))


def list_session_runs(session_id: str) -> list[Run]:
    """All the runs of a session, newest first (through their prompts)."""
    with open_db() as db:
        query = (
            select(Run)
            .join(Prompt, Prompt.id == Run.prompt_id)
            .where(Prompt.session_id == session_id)
            .order_by(Run.started_at.desc())
        )
        return list(db.exec(query))


def update_run(run_id: int, **changes) -> Run | None:
    """update_run(12, status="failed", reason="...") -> the updated run, None if there's no such run."""
    return update(Run, run_id, changes)


def delete_run(run_id: int) -> bool:
    """Delete the run, its steps and its screenshot. False if there was no such run."""
    with open_db() as db:
        run = db.get(Run, run_id)
        if run is None:
            return False
        delete_run_rows(db, run)
        db.commit()
        return True


# ── steps ───────────────────────────────────────────────────────────────────

def add_steps(run_id: int, lines: list[str]) -> list[Step]:
    """Save a run's timeline, as the pipeline writes it:

        "executor: aria-label ✔ 1 match, the right one"  ->  part "executor", ok True
    """
    steps = []
    for position, line in enumerate(lines, start=1):
        part, message = split_line(line)
        steps.append(Step(run_id=run_id, position=position, part=part, message=message, ok=ok_of(message)))

    with open_db() as db:
        db.add_all(steps)
        db.commit()
    return steps


def list_steps(run_id: int) -> list[Step]:
    """The run's timeline, in order."""
    with open_db() as db:
        query = select(Step).where(Step.run_id == run_id).order_by(Step.position)
        return list(db.exec(query))


def update_step(step_id: int, **changes) -> Step | None:
    return update(Step, step_id, changes)


def delete_step(step_id: int) -> bool:
    with open_db() as db:
        step = db.get(Step, step_id)
        if step is None:
            return False
        db.delete(step)
        db.commit()
        return True


def split_line(line: str) -> tuple[str, str]:
    """ "laya: picked Inspirations (link)"  ->  ("laya", "picked Inspirations (link)")"""
    part, separator, message = line.partition(":")
    if not separator:
        return "pipeline", line.strip()
    return part.strip(), message.strip()


def ok_of(message: str) -> bool | None:
    if "✔" in message:
        return True
    if "✘" in message:
        return False
    return None


# ── screenshots ─────────────────────────────────────────────────────────────

def save_screenshot(
    run_id: int,
    image: bytes | str,
    width: int | None = None,
    height: int | None = None,
    highlight: dict | None = None,
) -> Screenshot:
    """Save (or replace) the run's screenshot. `image`: JPEG bytes, or base64 as the executor gives it."""
    if isinstance(image, str):
        image = base64.b64decode(image)

    with open_db() as db:
        screenshot = db.get(Screenshot, run_id)
        if screenshot is None:
            screenshot = Screenshot(run_id=run_id, image=image)
        screenshot.image = image
        screenshot.width = width
        screenshot.height = height
        screenshot.highlight = highlight
        db.add(screenshot)
        db.commit()
        return screenshot


def get_screenshot(run_id: int) -> Screenshot | None:
    with open_db() as db:
        return db.get(Screenshot, run_id)


def screenshot_base64(run_id: int) -> str | None:
    """The run's screenshot as base64, the way the UI shows it. None if there's none."""
    screenshot = get_screenshot(run_id)
    if screenshot is None:
        return None
    return base64.b64encode(screenshot.image).decode()


def has_screenshot(run_id: int) -> bool:
    """Without loading the image."""
    with open_db() as db:
        return db.exec(select(Screenshot.run_id).where(Screenshot.run_id == run_id)).first() is not None


def screenshot_highlight(run_id: int) -> dict | None:
    """The element's box on the run's screenshot, without loading the image."""
    with open_db() as db:
        return db.exec(select(Screenshot.highlight).where(Screenshot.run_id == run_id)).first()


def delete_screenshot(run_id: int) -> bool:
    with open_db() as db:
        screenshot = db.get(Screenshot, run_id)
        if screenshot is None:
            return False
        db.delete(screenshot)
        db.commit()
        return True


# ── history: a session and everything under it ──────────────────────────────

def session_history(session_id: str) -> SessionHistory | None:
    """The session, its prompts in chain order, each prompt's runs (newest first) with their steps."""
    session = get_session(session_id)
    if session is None:
        return None

    prompts = []
    for prompt in list_prompts(session_id):
        runs = []
        for run in list_runs(prompt.id):
            runs.append(run_history(run))
        prompts.append(PromptHistory(prompt=prompt, runs=runs))
    return SessionHistory(session=session, prompts=prompts)


def run_history(run: Run) -> RunHistory:
    return RunHistory(
        run=run,
        steps=list_steps(run.id),
        has_screenshot=has_screenshot(run.id),
        highlight=screenshot_highlight(run.id),
    )


# ── shared helpers ──────────────────────────────────────────────────────────

def add(row):
    """Save a new row and give it back with its id."""
    with open_db() as db:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row


def update(model, row_id, changes: dict):
    """Change some fields of one row. None if there's no such row. Unknown field names are an error."""
    with open_db() as db:
        row = db.get(model, row_id)
        if row is None:
            return None
        for field, value in changes.items():
            if field not in model.model_fields:
                raise ValueError(f"{model.__name__} has no field {field!r}")
            setattr(row, field, value)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row


def delete_prompt_rows(db: DbSession, prompt: Prompt) -> None:
    """A prompt and everything under it, inside an open connection (the caller commits)."""
    for run in list(db.exec(select(Run).where(Run.prompt_id == prompt.id))):
        delete_run_rows(db, run)
    db.flush()  # children first: the foreign keys refuse a prompt deleted before its runs
    db.delete(prompt)


def delete_run_rows(db: DbSession, run: Run) -> None:
    """A run, its steps and its screenshot, inside an open connection (the caller commits)."""
    for step in list(db.exec(select(Step).where(Step.run_id == run.id))):
        db.delete(step)
    screenshot = db.get(Screenshot, run.id)
    if screenshot is not None:
        db.delete(screenshot)
    db.flush()  # children first: the foreign keys refuse a run deleted before its steps
    db.delete(run)
