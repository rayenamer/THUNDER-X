"""Core logic: pick one element of the page for an instruction, with rules only.

    elements ──► context resolver ──► direct matcher ──► found       1 element
                 (where?)             (what?)            ambiguous   2+ matches       (in candidates)
                                                         not_found   0 matches, the interactive elements
                                                                     of the context  (in candidates)

`candidates` is what the next step (Laya, see thunderx/pipeline.py) chooses from.
"""

from thunderx.element_finder.context_resolver import resolve_context
from thunderx.element_finder.direct_matcher import match
from thunderx.element_finder.models import FindResult
from thunderx.nl_parser.models import ParsedInstruction
from thunderx.page_extractor.models import PageElement


def find(parsed: ParsedInstruction, elements: list[PageElement]) -> FindResult:
    """Context resolver first, then the direct matcher on what's left."""
    context = resolve_context(parsed.hint, elements)

    if not context.elements:
        result = FindResult(status="not_found", route="context_resolver", reason=context.reason)
    else:
        result = match(parsed, context.elements)
        if result.status == "not_found":
            result.candidates = interactive(context.elements)

    result.steps.insert(0, context.step)
    result.parsed = parsed
    return result


def interactive(elements: list[PageElement]) -> list[PageElement]:
    kept = []
    for element in elements:
        if element.interactive:
            kept.append(element)
    return kept
