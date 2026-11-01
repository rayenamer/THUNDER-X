"""LogsDb endpoints, mounted by thunderx/main.py: read and clean up the history."""

from fastapi import APIRouter, HTTPException, Response

from thunderx.logs_db import services as logs
from thunderx.logs_db.models import RunHistory, Session, SessionHistory

router = APIRouter(prefix="/logs", tags=["logs_db"])


@router.get("/sessions", response_model=list[Session])
def list_sessions() -> list[Session]:
    """Every recorded session, newest first."""
    return logs.list_sessions()


@router.get("/sessions/{session_id}", response_model=SessionHistory)
def session_history(session_id: str) -> SessionHistory:
    """A session's whole history: its prompts in chain order, each prompt's runs with their steps."""
    history = logs.session_history(session_id)
    if history is None:
        raise HTTPException(404, f"no session {session_id}")
    return history


@router.get("/runs/{run_id}", response_model=RunHistory)
def get_run(run_id: int) -> RunHistory:
    run = logs.get_run(run_id)
    if run is None:
        raise HTTPException(404, f"no run {run_id}")
    return logs.run_history(run)


@router.get("/runs/{run_id}/screenshot")
def get_screenshot(run_id: int) -> Response:
    """The page after the run, as a JPEG image (use it as an <img src>)."""
    screenshot = logs.get_screenshot(run_id)
    if screenshot is None:
        raise HTTPException(404, f"no screenshot for run {run_id}")
    return Response(content=screenshot.image, media_type="image/jpeg")


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    """The session and everything under it."""
    if not logs.delete_session(session_id):
        raise HTTPException(404, f"no session {session_id}")
    return {"deleted": session_id}


@router.delete("/prompts/{prompt_id}")
def delete_prompt(prompt_id: int) -> dict:
    """The prompt and its runs."""
    if not logs.delete_prompt(prompt_id):
        raise HTTPException(404, f"no prompt {prompt_id}")
    return {"deleted": prompt_id}


@router.delete("/runs/{run_id}")
def delete_run(run_id: int) -> dict:
    """The run, its steps and its screenshot."""
    if not logs.delete_run(run_id):
        raise HTTPException(404, f"no run {run_id}")
    return {"deleted": run_id}
