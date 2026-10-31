"""nl_parser endpoints, mounted by thunderx/main.py."""

from fastapi import APIRouter

from thunderx.nl_parser.models import ParsedInstruction, ParseRequest
from thunderx.nl_parser.services import parse

router = APIRouter(prefix="/nl-parser", tags=["nl_parser"])


@router.post("/parse", response_model=ParsedInstruction)
def parse_instruction(request: ParseRequest) -> ParsedInstruction:
    return parse(request.instruction)
