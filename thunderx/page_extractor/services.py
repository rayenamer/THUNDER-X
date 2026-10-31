"""Core logic: open a browser window with browser-use and list the elements of the page.

One window per session, kept open between steps (design §5): node 2 runs
on the page node 1 left behind.

    session = await open_session("https://opensource-demo.orangehrmlive.com")
    page = await extract(session.session_id)
    await close_session(session.session_id)

For saved pages (test cases), extract_once() opens a hidden window, reads the page and closes it.
"""

from uuid import uuid4

from browser_use import BrowserSession
from browser_use.dom.service import DomService

from thunderx.page_extractor import helpers as h
from thunderx.page_extractor.models import PageSnapshot, SessionInfo


class SessionNotFound(KeyError):
    pass


# session id -> its open browser window
_sessions: dict[str, BrowserSession] = {}


async def open_session(url: str, headless: bool = False) -> SessionInfo:
    """Open a browser window on `url`. It stays open until close_session()."""
    browser = BrowserSession(headless=headless, keep_alive=True, highlight_elements=False)
    await browser.start()
    await browser.navigate_to(url)

    session_id = uuid4().hex[:8]
    _sessions[session_id] = browser
    return await session_info(session_id)


async def navigate(session_id: str, url: str) -> SessionInfo:
    browser = get_browser(session_id)
    await browser.navigate_to(url)
    return await session_info(session_id)


async def session_info(session_id: str) -> SessionInfo:
    browser = get_browser(session_id)
    url = await browser.get_current_page_url()
    title = await browser.get_current_page_title()
    return SessionInfo(session_id=session_id, url=url, title=title)


async def extract(session_id: str, only_visible: bool = False) -> PageSnapshot:
    """List the elements of the page as it is right now in the session's window."""
    browser = get_browser(session_id)
    snapshot = await read_page(browser)
    snapshot.session_id = session_id

    if only_visible:
        visible = []
        for element in snapshot.elements:
            if element.visible:
                visible.append(element)
        snapshot.elements = visible
    return snapshot


async def extract_once(url: str) -> PageSnapshot:
    """Open a hidden window on `url`, list its elements, close it. For saved pages: file:///..."""
    browser = BrowserSession(headless=True, keep_alive=True, highlight_elements=False)
    await browser.start()
    try:
        await browser.navigate_to(url)
        return await read_page(browser)
    finally:
        await browser.kill()


async def read_page(browser: BrowserSession) -> PageSnapshot:
    """Ask browser-use for the page tree, then flatten it into our PageElements."""
    dom = DomService(browser, cross_origin_iframes=True)
    state, root, _timing = await dom.get_serialized_dom_tree()

    # browser-use's own list of clickable / typeable elements
    interactive_ids = set()
    for node in state.selector_map.values():
        interactive_ids.add(node.backend_node_id)

    elements = h.collect_elements(root, interactive_ids)
    url = await browser.get_current_page_url()
    title = await browser.get_current_page_title()
    return PageSnapshot(url=url, title=title, elements=elements)


async def close_session(session_id: str) -> None:
    browser = _sessions.pop(session_id, None)
    if browser is None:
        raise SessionNotFound(session_id)
    await browser.kill()


async def close_all() -> None:
    """Close every window. Called when the service stops."""
    for session_id in list(_sessions):
        await close_session(session_id)


def get_browser(session_id: str) -> BrowserSession:
    browser = _sessions.get(session_id)
    if browser is None:
        raise SessionNotFound(session_id)
    return browser
