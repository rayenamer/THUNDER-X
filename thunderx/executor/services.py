"""Core logic: run the XPath on the page, and in act mode, do the action (design step 6).

    1. validate    the XPath, then its alternatives: keep the first that matches only our element
    2. act         click / hover / type / select / check, with browser-use's element actions
    3. wait        until the page has settled (new page, new tab, single-page app, menu opening)
    4. check       that the action did what it should (page changed, field holds the text...)
    5. screenshot  the page as the action left it

validate mode stops after 1 (+ 5): it touches nothing, safe on real apps.

"Our element" = the same node in Chrome: we compare Chrome's own node id (backend_node_id,
recorded by page_extractor) with the node the XPath matched. Positions are not reliable for that.
"""

import json

from browser_use import BrowserSession
from browser_use.browser.events import SwitchTabEvent

from thunderx.executor import helpers as h
from thunderx.executor.models import ExecutionResult, Highlight, Mode
from thunderx.page_extractor.models import PageElement
from thunderx.xpath_builder.models import XPathResult

OBJECT_GROUP = "thunderx-executor"  # Chrome keeps the nodes we look at under this name, until we release them


async def execute(built: XPathResult, element: PageElement | None, browser: BrowserSession, mode: Mode) -> ExecutionResult:
    result = ExecutionResult(
        action=built.action,
        xpath=None,
        value=built.value,
        confidence=built.confidence,
        route=built.route,
        mode=mode,
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
        await validate(result, built, element, browser)                     # 1
        if mode == "act" and result.status == "verified":
            await act_and_check(result, element, browser)                   # 2, 3, 4

    await take_screenshot(result, browser, scroll_to_element=(mode == "validate"))  # 5
    return result


# ── 1. validate ─────────────────────────────────────────────────────────────

async def validate(result: ExecutionResult, built: XPathResult, element: PageElement, browser: BrowserSession) -> None:
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
    search = f"document.evaluate({json.dumps(xpath)}, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null)"
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


# ── 2, 3, 4. act, wait, check ───────────────────────────────────────────────

async def act_and_check(result: ExecutionResult, element: PageElement, browser: BrowserSession) -> None:
    page = await browser.get_current_page()
    target = await page.get_element(element.backend_node_id)
    tabs_before = len(await browser.get_tabs())
    before = await h.fingerprint(page)

    try:
        await do_action(result.action, result.value, target)                       # 2
    except Exception as error:
        result.status = "failed"
        result.reason = f"the {result.action} failed: {error}"
        result.steps.append(f"executor: {result.action} ✘ {error}")
        return
    result.steps.append(f"executor: {describe_action(result)} ✔ done")

    if len(await browser.get_tabs()) > tabs_before:                            # a link opened a new tab
        await browser.event_bus.dispatch(SwitchTabEvent())
        result.steps.append("executor: a new tab opened, switched to it")

    after = await h.wait_until_settled(browser)                                # 3
    result.steps.append("executor: page settled")

    effect = await expected_effect(result, target)                             # 4
    if effect is None:
        effect = h.what_changed(before, after)

    if effect is None:
        result.status = "no_change"
        result.reason = f"the {result.action} was done, but nothing changed on the page"
        result.steps.append("executor: ✘ nothing changed")
    else:
        result.effect = effect
        result.steps.append(f"executor: ✔ {effect}")


async def do_action(action: str | None, value: str | None, target) -> None:
    """One action on the element, with browser-use's element actions."""
    if action in (None, "click"):
        await target.click()
    elif action == "double_click":
        await target.click(click_count=2)
    elif action == "right_click":
        await target.click(button="right")
    elif action == "hover":
        await target.hover()
    elif action == "type":
        await target.fill(value or "")
    elif action == "select":
        await target.select_option(value or "")
    elif action == "check":
        await target.check()
    elif action == "uncheck":
        state = await control_state(target)
        if state and state.get("checked"):
            await target.click()
    else:
        raise ValueError(f"unknown action {action}")


async def expected_effect(result: ExecutionResult, target) -> str | None:
    """For form controls, the effect we expect is the control's own state. None: nothing specific to check."""
    if result.action not in ("type", "select", "check", "uncheck"):
        return None

    state = await control_state(target)
    if state is None:
        return None  # the element is gone (the page changed): the page fingerprint decides

    if result.action == "type" and state["value"] == (result.value or ""):
        return f"the field holds \"{result.value}\""
    if result.action == "select" and result.value and result.value in (state["selected"], state["value"]):
        return f"\"{result.value}\" is selected"
    if result.action == "check" and state["checked"] is True:
        return "it is checked"
    if result.action == "uncheck" and state["checked"] is False:
        return "it is unchecked"
    return None


async def control_state(target) -> dict | None:
    """The live value / checked / selected option of a form control. None if it can't be read."""
    try:
        return json.loads(await target.evaluate(h.CONTROL_STATE))
    except Exception:
        return None


def describe_action(result: ExecutionResult) -> str:
    """ "click",  "type \"john\"" """
    if result.value:
        return f"{result.action} \"{result.value}\""
    return result.action or "click"


# ── 5. screenshot ───────────────────────────────────────────────────────────

async def take_screenshot(result: ExecutionResult, browser: BrowserSession, scroll_to_element: bool) -> None:
    """The visible page, with the element's box when it's still on screen.

    validate: scroll the element to the middle first. act: don't touch the page any more
    (scrolling would close a hover menu, and after a click the element may be gone).
    """
    page = await browser.get_current_page()
    if page is None:
        return

    # After going to another page, the XPath could match a lookalike there: no box.
    went_elsewhere = (result.effect or "").startswith("went to")
    if result.xpath is not None and not went_elsewhere:
        try:
            box = json.loads(await page.evaluate(h.ELEMENT_BOX, result.xpath, scroll_to_element))
            if box:
                result.highlight = Highlight(**box)
        except Exception:
            pass

    try:
        result.screenshot = await page.screenshot(format="jpeg", quality=70)
        result.url = await browser.get_current_page_url()
    except Exception:  # no screenshot is not a reason to fail the step
        result.steps.append("executor: couldn't take a screenshot")
