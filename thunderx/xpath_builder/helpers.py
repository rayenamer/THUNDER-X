"""Write candidate XPaths for one element, most stable first (design step 2). No browser here.

    data-testid → id → aria-label / name / placeholder → text → text inside its section → linked label → position
"""

import re

from thunderx.page_extractor.models import PageElement

TEST_ID_ATTRIBUTES = ["data-testid", "data-test", "data-qa", "data-cy"]
HEADINGS = "self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6 or self::legend or @role='heading'"
LABELLED_TAGS = {"input", "select", "textarea"}

# Elements of the SVG / MathML namespaces: in an HTML page, XPath can't match them by plain name
# (//svg matches nothing), only by local-name(): //*[local-name()='svg'].
FOREIGN_TAGS = {
    "svg", "g", "path", "use", "circle", "ellipse", "rect", "line", "polyline", "polygon",
    "symbol", "defs", "text", "tspan", "foreignobject", "lineargradient", "radialgradient", "math",
}


def candidate_xpaths(element: PageElement) -> list[tuple[str, str]]:
    """Every XPath worth trying for this element, as (style, xpath), best first."""
    tag = name_test(element.tag)
    attributes = element.attributes
    candidates = []

    for attribute in TEST_ID_ATTRIBUTES:
        if attributes.get(attribute):
            candidates.append(("test id", f"//{tag}[@{attribute}={literal(attributes[attribute])}]"))

    element_id = attributes.get("id")
    if element_id and not looks_generated(element_id):
        candidates.append(("id", f"//{tag}[@id={literal(element_id)}]"))

    for attribute in ["aria-label", "name", "placeholder"]:
        if attributes.get(attribute):
            candidates.append((attribute, f"//{tag}[@{attribute}={literal(attributes[attribute])}]"))

    for text in texts_of(element):
        candidates.append(("text", f"//{tag}[normalize-space()={literal(text)}]"))

    if element.sections:
        section = element.sections[-1]  # the closest block around it
        for text in texts_of(element):
            candidates.append(("text in section", (
                f"//*[{HEADINGS}][normalize-space()={literal(section)}]/..//{tag}[normalize-space()={literal(text)}]"
            )))
            candidates.append(("text in section", (
                f"//*[@aria-label={literal(section)}]//{tag}[normalize-space()={literal(text)}]"
            )))

    if element.tag in LABELLED_TAGS and element_id and element.label:
        candidates.append(("linked label", (
            f"//{tag}[@id=//label[normalize-space()={literal(element.label)}]/@for]"
        )))

    candidates.append(("position", position_xpath(element.xpath)))  # breaks easily: last resort
    return candidates


def name_test(tag: str) -> str:
    """How an XPath names this tag:  "button" -> "button",  "svg" -> "*[local-name()='svg']"."""
    if tag in FOREIGN_TAGS:
        return f"*[local-name()='{tag}']"
    return tag


def position_xpath(path: str) -> str:
    """browser-use's path made absolute and SVG-safe:

        html/body/a[2]/svg/path  ->  /html/body/a[2]/*[local-name()='svg']/*[local-name()='path']
    """
    steps = []
    for segment in path.split("/"):
        match = re.fullmatch(r"([\w-]+)(\[\d+\])?", segment)
        if match:
            steps.append(name_test(match.group(1)) + (match.group(2) or ""))
        else:
            steps.append(segment)
    return "/" + "/".join(steps)


def texts_of(element: PageElement) -> list[str]:
    """The texts the element may show: its own text, then its label if different."""
    texts = []
    for text in [element.text, element.label]:
        if text and text not in texts:
            texts.append(text)
    return texts


def looks_generated(value: str) -> bool:
    """Ids a framework made up, which change on the next build:  ":r1:", "ember123", "a8f3c9e2b1"."""
    if value.startswith(":") or "__" in value:
        return True
    if re.search(r"\d{3,}", value):
        return True
    return re.fullmatch(r"[0-9a-f]{8,}", value) is not None


def literal(text: str) -> str:
    """A text as an XPath string, whatever quotes it contains:  it's -> "it's"."""
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat('" + "', \"'\", '".join(parts) + "')"
