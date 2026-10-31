"""page_extractor endpoints, mounted by thunderx/main.py."""

from fastapi import APIRouter, HTTPException

from thunderx.page_extractor import services
from thunderx.page_extractor.models import (
    ExtractRequest,
    NavigateRequest,
    OpenSessionRequest,
    PageSnapshot,
    SessionInfo,
)

router = APIRouter(prefix="/page-extractor", tags=["page_extractor"])


@router.post("/sessions", response_model=SessionInfo)
async def open_session(request: OpenSessionRequest) -> SessionInfo:
    """Open a browser window on a URL. It stays open between steps."""
    return await services.open_session(request.url, headless=request.headless)


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def session_info(session_id: str) -> SessionInfo:
    try:
        return await services.session_info(session_id)
    except services.SessionNotFound:
        raise HTTPException(404, f"no session {session_id}")


@router.post("/sessions/{session_id}/navigate", response_model=SessionInfo)
async def navigate(session_id: str, request: NavigateRequest) -> SessionInfo:
    try:
        return await services.navigate(session_id, request.url)
    except services.SessionNotFound:
        raise HTTPException(404, f"no session {session_id}")


@router.get("/sessions/{session_id}/elements", response_model=PageSnapshot)
async def extract(session_id: str, only_visible: bool = False) -> PageSnapshot:
    """List the elements of the page currently open in the session's window."""
    try:
        return await services.extract(session_id, only_visible=only_visible)
    except services.SessionNotFound:
        raise HTTPException(404, f"no session {session_id}")


@router.delete("/sessions/{session_id}")
async def close_session(session_id: str) -> dict:
    try:
        await services.close_session(session_id)
    except services.SessionNotFound:
        raise HTTPException(404, f"no session {session_id}")
    return {"closed": session_id}


@router.post("/extract", response_model=PageSnapshot)
async def extract_once(request: ExtractRequest) -> PageSnapshot:
    """One shot, no window to keep: open hidden, list the elements, close. Works with file:/// saved pages."""
    return await services.extract_once(request.url)
