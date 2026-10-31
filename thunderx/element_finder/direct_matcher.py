"""Direct matcher: find the target by what it says and what it is. No AI.

    "Click on about us"           ->  the one element saying "About us"           -> found
    "Click the second Save button" ->  the 2nd button saying "Save"                -> found
    "Click ok"  (two "ok" on page)  ->  can't choose                                -> ambiguous
    "Click sign in" (page says "Log in") -> nothing says "sign in"                  -> not_found

Ambiguous and not_found go to the next step (shortlist, Laya, LLM: design step 4).
"""

from thunderx.element_finder.models import FindResult
from thunderx.nl_parser.models import ParsedInstruction, Target
from thunderx.page_extractor.helpers import describe, has_role, says
from thunderx.page_extractor.models import PageElement

# Actions done on a control: prefer elements you can actually click or type in.
ACTIONS_ON_CONTROLS = {"click", "double_click", "right_click", "type", "select", "check", "uncheck"}


def match(parsed: ParsedInstruction, elements: list[PageElement]) -> FindResult:
    target = parsed.target
    if target.text is None and target.role is None:
        return not_found("the instruction doesn't say which element")

    if target.text is not None:
        matches = keep(elements, lambda element: says(element, target.text))
        # People say "button" for anything that looks like one (often a styled <a> link),
        # so with a text, the role only picks among the matches, it never removes them all.
        matches = prefer(matches, lambda element: has_role(element, target.role))
    else:
        # No text ("click the last link"): the role is all we have, so it filters.
        matches = keep(elements, lambda element: has_role(element, target.role))

    # Same text twice is often one thing drawn twice (<a> around an <img>, a hidden copy for mobile...)
    matches = prefer(matches, lambda element: element.visible)
    if parsed.action in ACTIONS_ON_CONTROLS:
        matches = prefer(matches, lambda element: element.interactive)

    if target.ordinal is not None:
        return pick_by_ordinal(matches, target)

    if not matches:
        return not_found(f"nothing on the page matches {name_of(target)}")
    if len(matches) == 1:
        return found(matches[0])
    return FindResult(
        status="ambiguous",
        candidates=matches,
        route="direct_matcher",
        reason=f"{len(matches)} elements match {name_of(target)}: which one?",
        steps=[f"direct matcher: {len(matches)} matches"],
    )


def pick_by_ordinal(matches: list[PageElement], target: Target) -> FindResult:
    """ "the second Save button": the 2nd one in page order. -1 is the last one."""
    in_page_order = sorted(matches, key=lambda element: element.index)

    if target.ordinal == -1 and in_page_order:
        return found(in_page_order[-1])
    if 1 <= target.ordinal <= len(in_page_order):
        return found(in_page_order[target.ordinal - 1])
    return not_found(f"asked for number {target.ordinal}, but only {len(in_page_order)} match {name_of(target)}")


def found(element: PageElement) -> FindResult:
    return FindResult(
        status="found",
        element=element,
        confidence=1.0,
        route="direct_matcher",
        steps=[f"direct matcher: 1 match -> {describe(element)}"],
    )


def not_found(reason: str) -> FindResult:
    return FindResult(status="not_found", route="direct_matcher", reason=reason, steps=["direct matcher: 0 matches"])


def keep(elements: list[PageElement], condition) -> list[PageElement]:
    kept = []
    for element in elements:
        if condition(element):
            kept.append(element)
    return kept


def prefer(elements: list[PageElement], condition) -> list[PageElement]:
    """Keep the elements where condition is true, unless that would leave none."""
    preferred = keep(elements, condition)
    if preferred:
        return preferred
    return elements


def name_of(target: Target) -> str:
    """ "'Save' button",  "'about us'",  "dropdown"  (for messages)."""
    if target.text and target.role:
        return f"'{target.text}' {target.role}"
    if target.text:
        return f"'{target.text}'"
    return f"a {target.role}"
