"""Data classes: what the executor gives back."""

from typing import Literal

from pydantic import BaseModel

from thunderx.nl_parser.models import Action

Status = Literal["verified", "failed", "not_found"]


class Highlight(BaseModel):
    """Where the element is in the screenshot, in pixels of the visible page."""

    x: float
    y: float
    width: float
    height: float
    viewport_width: float
    viewport_height: float


class ExecutionResult(BaseModel):
    """The XPath after it ran on the page.

        {"action": "click", "xpath": "//a[normalize-space()='Today']", "value": null,
         "confidence": 1.0, "status": "verified"}
    """

    action: Action | None
    xpath: str | None          # the first XPath that matched exactly our element. None: none did
    value: str | None = None
    confidence: float = 0.0
    route: str | None = None   # which part picked the element: "direct_matcher", "laya"
    status: Status             # verified: ran on the page, 1 match, the right one
    reason: str | None = None  # why it failed / wasn't found
    steps: list[str] = []      # what every part did, for the node timeline
    url: str | None = None                # the page it ran on
    screenshot: str | None = None         # the visible page after the run, base64 JPEG
    highlight: Highlight | None = None    # the element's box in that screenshot
