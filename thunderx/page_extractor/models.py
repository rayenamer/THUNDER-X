"""Data classes: what page_extractor takes in and gives back."""

from pydantic import BaseModel


class Box(BaseModel):
    """Where the element is drawn, in page coordinates (used for "next to", "below"...)."""

    x: float
    y: float
    width: float
    height: float


class PageElement(BaseModel):
    """One element of the page, as element_finder will see it.

        <section><h2>Employee</h2><span>ok</span></section>
        ->  tag="span", label="ok", text="ok", sections=["Employee"]
    """

    index: int                       # its number in this snapshot
    tag: str                         # "button", "span", "select"...
    role: str | None = None          # what Chrome says it is: "button", "link", "combobox"...
    label: str | None = None         # what a person would call it: "Country" for the select next to "Country"
    text: str | None = None          # its own visible text
    sections: list[str] = []         # headings of the blocks around it, outermost first
    attributes: dict[str, str] = {}  # id, data-testid, name, aria-label... (for xpath_builder)
    interactive: bool = False        # can be clicked / typed into (browser-use's opinion)
    visible: bool = False
    box: Box | None = None
    xpath: str                       # browser-use's position XPath (body/nav/a[2]): last resort only
    backend_node_id: int             # Chrome's id for the element, to find it again (executor)
    frame_id: str | None = None      # set when the element lives inside an iframe


class PageSnapshot(BaseModel):
    session_id: str | None = None
    url: str
    title: str
    elements: list[PageElement]


class SessionInfo(BaseModel):
    session_id: str
    url: str
    title: str


class OpenSessionRequest(BaseModel):
    url: str
    headless: bool = False  # False: a real window the user can watch


class NavigateRequest(BaseModel):
    url: str


class ExtractRequest(BaseModel):
    url: str  # a live site, or a saved page: file:///path/to/page.html
