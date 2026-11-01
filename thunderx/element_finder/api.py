"""element_finder endpoints, mounted by thunderx/main.py."""

from fastapi import APIRouter

from thunderx.element_finder.models import FindRequest, FindResult
from thunderx.element_finder.services import find

router = APIRouter(prefix="/element-finder", tags=["element_finder"])


@router.post("/find", response_model=FindResult)
def find_element(request: FindRequest) -> FindResult:
    """Rules only: nl_parser's output + page_extractor's output -> one element, or the candidates left."""
    return find(request.parsed, request.elements)
