"""Core logic: write the XPath for the picked element. No browser: the executor runs it.

Takes the result of element_finder / laya and gives {action, xpath, value, confidence},
with the next XPath styles as alternatives, best first.
"""

from thunderx.element_finder.models import FindResult
from thunderx.xpath_builder import helpers as h
from thunderx.xpath_builder.models import XPathOption, XPathResult


def build(found: FindResult) -> XPathResult:
    parsed = found.parsed
    result = XPathResult(
        action=parsed.action,
        xpath=None,
        value=parsed.value,
        confidence=found.confidence,
        route=found.route,
        steps=list(found.steps),
    )

    if found.status != "found" or found.element is None:
        result.reason = found.reason or "no element picked"
        return result

    options = []
    for style, xpath in h.candidate_xpaths(found.element):
        options.append(XPathOption(style=style, xpath=xpath))

    best = options[0]
    result.xpath = best.xpath
    result.style = best.style
    result.alternatives = options[1:]
    result.steps.append(f"xpath builder: {len(options)} XPaths written, best: {best.style}")
    return result
