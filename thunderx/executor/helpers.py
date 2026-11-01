"""Small pieces the executor uses: scripts run in the page, and the page "fingerprint"."""

import asyncio
import json
import time

# Where the element matched by an XPath is drawn (visible-page coordinates).
# scroll=true first brings it to the middle of the screen.
ELEMENT_BOX = """(xpath, scroll) => {
  const node = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
  if (!node) return {};
  if (scroll) node.scrollIntoView({block: "center", inline: "center"});
  const box = node.getBoundingClientRect();
  if (box.width === 0 && box.height === 0) return {};
  return {x: box.x, y: box.y, width: box.width, height: box.height,
          viewport_width: window.innerWidth, viewport_height: window.innerHeight};
}"""

# A cheap summary of the page: if any of it changes, the page changed.
FINGERPRINT = """() => ({
  url: location.href,
  title: document.title,
  ready: document.readyState,
  elements: document.getElementsByTagName("*").length,
  size: document.documentElement.outerHTML.length,
})"""

# The live state of a form control, run on the element itself (`this`).
CONTROL_STATE = """() => ({
  value: this.value ?? null,
  checked: this.checked ?? null,
  selected: this.tagName === "SELECT" && this.selectedIndex >= 0 ? this.options[this.selectedIndex].text.trim() : null,
})"""

SETTLE_TIMEOUT_SECONDS = 10
QUIET_SECONDS = 0.5  # the page has settled when nothing changed for this long
POLL_SECONDS = 0.25


async def fingerprint(page) -> dict | None:
    """The page's fingerprint. None while it can't answer (in the middle of loading a new page)."""
    try:
        return json.loads(await page.evaluate(FINGERPRINT))
    except Exception:
        return None


async def wait_until_settled(browser) -> dict | None:
    """Wait until the page is loaded and stopped changing. Returns its last fingerprint.

    Works for a new page (load event), a single-page app (no load event, the content changes),
    and a menu or tooltip opening (part of the page changes).
    """
    deadline = time.monotonic() + SETTLE_TIMEOUT_SECONDS
    previous = None
    quiet_since = None

    while time.monotonic() < deadline:
        await asyncio.sleep(POLL_SECONDS)
        page = await browser.get_current_page()  # a new tab or a new page: ask again each time
        current = await fingerprint(page) if page else None

        if current is None or current["ready"] != "complete" or current != previous:
            previous = current
            quiet_since = time.monotonic()
            continue
        if time.monotonic() - quiet_since >= QUIET_SECONDS:
            return current

    return previous  # still moving after the timeout: carry on with what we have


def what_changed(before: dict | None, after: dict | None) -> str | None:
    """ "went to https://…", "the page changed", or None when it looks the same."""
    if not before or not after:
        return "the page changed"
    if after["url"] != before["url"]:
        return f"went to {after['url']}"
    if after["title"] != before["title"]:
        return f"the page title is now \"{after['title']}\""
    if after["elements"] != before["elements"] or after["size"] != before["size"]:
        return "the page changed"
    return None
