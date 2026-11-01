"""The pipeline: each part's output is the next part's input.

    instruction ─► nl_parser ──────┐
                                   ├─► element_finder ─► laya ─► (xpath_builder, executor: later)
    page ───────► page_extractor ──┘

Every part stays independent; only this file knows the order.
"""

from pydantic import BaseModel

from thunderx.element_finder import services as element_finder
from thunderx.element_finder.models import FindResult
from thunderx.laya import services as laya
from thunderx.nl_parser import services as nl_parser
from thunderx.page_extractor import services as page_extractor
from thunderx.page_extractor.models import PageElement


class RunRequest(BaseModel):
    session_id: str   # a window opened with POST /page-extractor/sessions
    instruction: str  # "Hover over ok under Employee section"


async def find_element(instruction: str, elements: list[PageElement]) -> FindResult:
    parsed = nl_parser.parse(instruction)
    result = element_finder.find(parsed, elements)  # rules: context resolver + direct matcher
    result = await laya.decide(result)               # only acts if the rules didn't find it
    return result


async def run_in_session(session_id: str, instruction: str) -> FindResult:
    """On the page open in a session's window, as it is right now."""
    page = await page_extractor.extract(session_id)
    return await find_element(instruction, page.elements)
