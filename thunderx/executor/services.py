"""Core logic: run the XPaths on the page (design step 6, validate mode).

Takes xpath_builder's result, tries its XPath then the alternatives, and keeps the first one
that matches exactly 1 element, the right one (design rule 1: never return an XPath we haven't run).
Then takes a screenshot of the page, with the element's box, so the user can see what was picked.

"The right one" = the same node in Chrome: we compare Chrome's own node id (backend_node_id,
recorded by page_extractor) with the node the XPath matched. Positions are not reliable for that:
scrolling, sticky footers and animations move elements around.

Act mode (do the click / hover / type, then check something changed) comes later.
"""

import json

from browser_use import BrowserSession

from thunderx.executor.models import ExecutionResult, Highlight
from thunderx.page_extractor.models import PageElement
from thunderx.xpath_builder.models import XPathResult

OBJECT_GROUP = "thunderx-executor"  # Chrome keeps the nodes we look at under this name, until we release them

# Scrolls the element to the middle of the screen and says where it is drawn (visible-page coordinates).
SHOW_ELEMENT = """(xpath) => {
  const node = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
  if (!node) return {};
  node.scrollIntoView({block: "center", inline: "center"});
  const box = node.getBoundingClientRect();
  return {x: box.x, y: box.y, width: box.width, height: box.height,
          viewport_width: window.innerWidth, viewport_height: window.innerHeight};
}"""


async def validate(built: XPathResult, element: PageElement | None, browser: BrowserSession) -> ExecutionResult:
    """Run each XPath on the page, best first; keep the first that matches only our element."""
    result = ExecutionResult(
        action=built.action,
        xpath=None,
        value=built.value,
        confidence=built.confidence,
        route=built.route,
        status="not_found",
        steps=list(built.steps),
    )

    page = await browser.get_current_page()
    if page is None:
        result.status = "failed"
        result.reason = "no page open in the browser"
        return result

    if built.xpath is None or element is None:
        result.reason = built.reason or "no XPath to run"
    else:
        await try_xpaths(result, built, element, browser)

    await take_screenshot(result, page, browser)
    return result


async def try_xpaths(result: ExecutionResult, built: XPathResult, element: PageElement, browser: BrowserSession) -> None:
    """The XPath, then its alternatives: the first one that matches only our element wins."""
    tries = [(built.style, built.xpath)]
    for option in built.alternatives:
        tries.append((option.style, option.xpath))

    cdp = await browser.get_or_create_cdp_session(focus=False)
    try:
        for style, xpath in tries:
            match = await match_on_page(cdp, xpath)

            if match is None:
                result.steps.append(f"executor: {style} ✘ couldn't run on this page")
                continue
            count, node_id = match
            if count != 1:
                result.steps.append(f"executor: {style} ✘ {count} matches")
                continue
            if node_id != element.backend_node_id:
                result.steps.append(f"executor: {style} ✘ 1 match, but another element")
                continue

            result.steps.append(f"executor: {style} ✔ 1 match, the right one")
            result.xpath = xpath
            result.status = "verified"
            return
    finally:
        await release_nodes(cdp)

    result.status = "failed"
    result.reason = "no XPath matched exactly this element on the page"


async def match_on_page(cdp, xpath: str) -> tuple[int, int | None] | None:
    """How many elements the XPath matches, and Chrome's node id of the match when there's exactly one.

    None if the browser couldn't run it (bad XPath, page gone, element in an iframe...).
    """
    search = (
        f"document.evaluate({json.dumps(xpath)}, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null)"
    )
    try:
        counted = await evaluate(cdp, f"{search}.snapshotLength", by_value=True)
        count = counted["result"]["value"]
        if count != 1:
            return count, None

        found = await evaluate(cdp, f"{search}.snapshotItem(0)", by_value=False)
        described = await cdp.cdp_client.send.DOM.describeNode(
            params={"objectId": found["result"]["objectId"]}, session_id=cdp.session_id
        )
        return 1, described["node"]["backendNodeId"]
    except Exception:
        return None


async def evaluate(cdp, expression: str, by_value: bool) -> dict:
    """Run JavaScript in the page. by_value: get the value itself, else a handle on the object."""
    answer = await cdp.cdp_client.send.Runtime.evaluate(
        params={"expression": expression, "returnByValue": by_value, "objectGroup": OBJECT_GROUP},
        session_id=cdp.session_id,
    )
    if "exceptionDetails" in answer:
        raise RuntimeError(answer["exceptionDetails"])
    return answer


async def release_nodes(cdp) -> None:
    try:
        await cdp.cdp_client.send.Runtime.releaseObjectGroup(
            params={"objectGroup": OBJECT_GROUP}, session_id=cdp.session_id
        )
    except Exception:
        pass


async def take_screenshot(result: ExecutionResult, page, browser: BrowserSession) -> None:
    """The visible page, with the element in the middle and its box, when there is one."""
    if result.xpath is not None:
        try:
            box = json.loads(await page.evaluate(SHOW_ELEMENT, result.xpath))
            if box:
                result.highlight = Highlight(**box)
        except Exception:
            pass

    try:
        result.screenshot = await page.screenshot(format="jpeg", quality=70)
        result.url = await browser.get_current_page_url()
    except Exception:  # no screenshot is not a reason to fail the step
        result.steps.append("executor: couldn't take a screenshot")
