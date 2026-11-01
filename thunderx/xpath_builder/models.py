"""Data classes: what xpath_builder gives back."""

from pydantic import BaseModel

from thunderx.nl_parser.models import Action


class XPathOption(BaseModel):
    style: str  # "test id", "id", "text", "text in section", "position"...
    xpath: str


class XPathResult(BaseModel):
    """
        {"action": "click", "xpath": "//header//button[normalize-space()='Type']", "value": null, "confidence": 0.93}
    """

    action: Action | None
    xpath: str | None                    # the most stable XPath for the element. None: no element was picked
    value: str | None = None             # text to type / option to pick
    confidence: float = 0.0
    route: str | None = None             # which part picked the element: "direct_matcher", "laya"
    style: str | None = None             # which style `xpath` is
    alternatives: list[XPathOption] = [] # the next styles, best first: the executor tries them if `xpath` fails
    reason: str | None = None            # why there is no XPath
    steps: list[str] = []                # what every part did, for the node timeline
