"""Core logic: pick one element of the page for an instruction.

    elements ──► context resolver ──► direct matcher ──► found       → xpath_builder
                 (where?)             (what?)            ambiguous   → shortlist / Laya / LLM (later)
                                                         not_found   → NOT_FOUND + reason
"""

from thunderx.element_finder.context_resolver import resolve_context
from thunderx.element_finder.direct_matcher import match
from thunderx.element_finder.models import FindResult
from thunderx.nl_parser.models import ParsedInstruction
from thunderx.nl_parser.services import parse
from thunderx.page_extractor import services as page_extractor
from thunderx.page_extractor.models import PageElement


def find(parsed: ParsedInstruction, elements: list[PageElement]) -> FindResult:
    """Context resolver first, then the direct matcher on what's left."""
    context = resolve_context(parsed.hint, elements)

    if not context.elements:
        result = FindResult(status="not_found", route="context_resolver", reason=context.reason)
    else:
        result = match(parsed, context.elements)

    result.steps.insert(0, context.step)
    result.parsed = parsed
    return result


async def find_in_session(session_id: str, instruction: str) -> FindResult:
    """The pipeline so far: read the instruction, read the page open in the session, find the element."""
    parsed = parse(instruction)
    page = await page_extractor.extract(session_id)
    return find(parsed, page.elements)
