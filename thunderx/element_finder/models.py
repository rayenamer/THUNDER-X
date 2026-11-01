"""Data classes: what element_finder takes in and gives back."""

from typing import Literal

from pydantic import BaseModel

from thunderx.nl_parser.models import ParsedInstruction
from thunderx.page_extractor.models import PageElement

Status = Literal["found", "ambiguous", "not_found"]


class Context(BaseModel):
    """What the context resolver leaves for the direct matcher."""

    elements: list[PageElement]   # the elements that fit the hint
    step: str                     # what it did, for the timeline: "1022 elements -> 12 inside 'Employee'"
    reason: str | None = None     # why nothing is left, if nothing is left


class FindResult(BaseModel):
    status: Status
    element: PageElement | None = None       # the pick, when found
    candidates: list[PageElement] = []       # what the next step chooses from (matches, or the context)
    confidence: float = 0.0
    route: str | None = None                 # which part answered: "direct_matcher", "laya"
    reason: str | None = None                # when not found / ambiguous: "2 elements say 'Save', which one?"
    steps: list[str] = []                    # what each part did, in order (the node timeline)
    parsed: ParsedInstruction | None = None  # how the instruction was read


class FindRequest(BaseModel):
    parsed: ParsedInstruction    # nl_parser's output
    elements: list[PageElement]  # page_extractor's output
