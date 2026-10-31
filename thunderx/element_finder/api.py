"""element_finder endpoints, mounted by thunderx/main.py."""

from fastapi import APIRouter, HTTPException

from thunderx.element_finder.models import FindRequest, FindResult
from thunderx.element_finder.services import find_in_session
from thunderx.page_extractor.services import SessionNotFound

router = APIRouter(prefix="/element-finder", tags=["element_finder"])


@router.post("/find", response_model=FindResult)
async def find(request: FindRequest) -> FindResult:
    """Pick the element an instruction points at, on the page open in a session."""
    try:
        return await find_in_session(request.session_id, request.instruction)
    except SessionNotFound:
        raise HTTPException(404, f"no session {request.session_id}")
