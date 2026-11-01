"""Data classes: what the executor gives back."""

from typing import Literal

from pydantic import BaseModel

from thunderx.nl_parser.models import Action

# validate: check the XPath only, touch nothing (safe on real apps)
# act:      check the XPath, then do the action and check it worked
Mode = Literal["validate", "act"]

# verified:  the XPath matched only our element (and, in act mode, the action worked)
# no_change: act mode, the action was done but nothing visible changed: maybe it didn't work
# failed:    an element was picked, but no XPath matched only it, or the action failed
# not_found: no element was picked
Status = Literal["verified", "no_change", "failed", "not_found"]


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
         "confidence": 1.0, "status": "verified", "effect": "went to https://..."}
    """

    action: Action | None
    xpath: str | None          # the first XPath that matched exactly our element. None: none did
    value: str | None = None
    confidence: float = 0.0
    route: str | None = None   # which part picked the element: "direct_matcher", "laya"
    mode: Mode = "validate"
    status: Status
    effect: str | None = None  # act mode: what the action changed ("went to …", "the field holds …")
    reason: str | None = None  # why it failed / wasn't found
    steps: list[str] = []      # what every part did, for the node timeline
    url: str | None = None                # the page after the run
    screenshot: str | None = None         # the visible page after the run, base64 JPEG
    highlight: Highlight | None = None    # the element's box in that screenshot
