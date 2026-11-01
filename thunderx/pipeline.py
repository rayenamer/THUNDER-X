"""The pipeline: each part's output is the next part's input.

    instruction ─► nl_parser ──────┐
                                   ├─► element_finder ─► laya ─► xpath_builder ─► executor
    page ───────► page_extractor ──┘

Every part stays independent; only this file knows the order.
"""

from pydantic import BaseModel

from thunderx.element_finder import services as element_finder
from thunderx.executor import services as executor
from thunderx.executor.models import ExecutionResult
from thunderx.laya import services as laya
from thunderx.nl_parser import services as nl_parser
from thunderx.page_extractor import services as page_extractor
from thunderx.xpath_builder import services as xpath_builder


class RunRequest(BaseModel):
    session_id: str   # a window opened with POST /page-extractor/sessions
    instruction: str  # "Hover over ok under Employee section"


async def run_in_session(session_id: str, instruction: str) -> ExecutionResult:
    """On the page open in a session's window, as it is right now."""
    page = await page_extractor.extract(session_id)
    parsed = nl_parser.parse(instruction)

    found = element_finder.find(parsed, page.elements)  # rules: context resolver + direct matcher
    found = await laya.decide(found)                     # only acts if the rules didn't find it
    built = xpath_builder.build(found)                   # writes the XPaths, no browser

    browser = page_extractor.get_browser(session_id)
    return await executor.validate(built, found.element, browser)  # runs them on the page
