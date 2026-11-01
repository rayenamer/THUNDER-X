"""Context resolver: use the "where" of the instruction to narrow down the page.

It runs before the direct matcher and removes the elements that don't fit the hint.

    "Hover over ok under Employee section"  ->  keep only what sits in the "Employee" section
    "Select the dropdown next to Country"   ->  keep what is close to the "Country" text
    "team section under the login button"   ->  keep what is below the "login" button

When the hint can't be found on the page, nothing is kept, and the reason says why.
"""

from thunderx.element_finder.models import Context
from thunderx.nl_parser.helpers import contains_words
from thunderx.nl_parser.models import Hint
from thunderx.page_extractor.helpers import distance, has_role, says
from thunderx.page_extractor.models import PageElement

NEAR_DISTANCE = 200  # pixels between centers to count as "next to"


def resolve_context(hint: Hint | None, elements: list[PageElement]) -> Context:
    total = len(elements)

    if hint is None:
        return Context(elements=elements, step=f"no hint: kept all {total} elements")

    if hint.text is None:  # "in the dialog": nothing to look for by name yet
        return Context(elements=elements, step=f"hint '{hint.relation} {hint.role}' has no name: kept all {total} elements")

    if hint.relation == "within":
        return inside_section(hint, elements)
    return around_anchor(hint, elements)


def inside_section(hint: Hint, elements: list[PageElement]) -> Context:
    """Keep the elements whose section headings mention the hint:  "under Employee"."""
    kept = []
    for element in elements:
        for section in element.sections:
            if contains_words(section, hint.text):
                kept.append(element)
                break

    if kept:
        return Context(elements=kept, step=f"context: {len(elements)} elements -> {len(kept)} inside '{hint.text}'")

    # No block is titled like that: the hint may name an element, not a section.
    # "Today under App Store for iPhone": a menu title, with "Today" below it.
    below = around_anchor(Hint(relation="below", text=hint.text, role=hint.role), elements)
    if below.elements:
        below.step = f"context: no section called '{hint.text}', took what is below it instead: {below.step}"
        return below

    return Context(
        elements=[],
        step="context: nothing kept",
        reason=f"no section called '{hint.text}', and nothing on the page says '{hint.text}'",
    )


def around_anchor(hint: Hint, elements: list[PageElement]) -> Context:
    """Keep the elements placed next to / above / below... the anchor:  "next to Country"."""
    anchors = find_anchors(hint, elements)
    if not anchors:
        return Context(elements=[], step="context: nothing kept", reason=f"nothing on the page says '{hint.text}'")

    kept = []
    for element in elements:
        if hint.relation == "near" and element in anchors:
            # the <select> named "Country" by its <label> is itself an anchor: keep it
            kept.append(element)
        elif fits(element, anchors, hint.relation):
            kept.append(element)

    if not kept:
        return Context(elements=[], step="context: nothing kept", reason=f"nothing is {hint.relation} '{hint.text}'")

    # nearest first
    kept.sort(key=lambda element: distance_to_anchors(element, anchors))
    return Context(elements=kept, step=f"context: {len(elements)} elements -> {len(kept)} {hint.relation} '{hint.text}'")


def find_anchors(hint: Hint, elements: list[PageElement]) -> list[PageElement]:
    """The elements the hint points at: the ones saying "Country" (and being a "button", if it says so)."""
    named = []
    for element in elements:
        if says(element, hint.text):
            named.append(element)

    with_role = []
    for element in named:
        if has_role(element, hint.role):
            with_role.append(element)

    if with_role:
        return with_role
    return named  # the role didn't match anything: trust the name alone


def fits(element: PageElement, anchors: list[PageElement], relation: str) -> bool:
    """Is the element placed `relation` to at least one anchor?"""
    if element.box is None or element in anchors:
        return False

    x = element.box.x + element.box.width / 2
    y = element.box.y + element.box.height / 2

    for anchor in anchors:
        box = anchor.box
        if box is None:
            continue
        if relation == "near" and distance(element.box, box) <= NEAR_DISTANCE:
            return True
        if relation == "below" and y > box.y + box.height:
            return True
        if relation == "above" and y < box.y:
            return True
        if relation == "left_of" and x < box.x:
            return True
        if relation == "right_of" and x > box.x + box.width:
            return True
    return False


def distance_to_anchors(element: PageElement, anchors: list[PageElement]) -> float:
    """Pixels to the closest anchor. Elements without a box go last."""
    closest = float("inf")
    for anchor in anchors:
        if element.box is not None and anchor.box is not None:
            closest = min(closest, distance(element.box, anchor.box))
    return closest
