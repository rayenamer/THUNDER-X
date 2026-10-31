"""Turn browser-use's DOM tree into a flat list of PageElement. No browser calls here."""

import re

from browser_use.dom.views import EnhancedDOMTreeNode, NodeType

from thunderx.page_extractor.models import Box, PageElement

# Not part of what the user sees: skip them and everything inside.
SKIPPED_BLOCKS = {"head", "script", "style", "noscript", "template"}

# Wrappers we walk through but don't list.
WRAPPER_TAGS = {"html", "body"}

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "legend", "caption", "summary"}

# Blocks that group other elements. Their heading names the section.
CONTAINER_TAGS = {"section", "form", "fieldset", "dialog", "nav", "header", "footer", "aside", "main", "article", "table"}
CONTAINER_ROLES = {"region", "dialog", "alertdialog", "form", "navigation", "group", "tabpanel", "banner", "contentinfo"}

# Chrome roles that say nothing useful.
EMPTY_ROLES = {"generic", "none", "presentation", "StaticText", "InlineTextBox"}

# Attributes xpath_builder can build a stable XPath from, best first.
KEPT_ATTRIBUTES = [
    "data-testid", "data-test", "data-qa", "data-cy", "id", "name", "aria-label", "aria-labelledby",
    "placeholder", "title", "alt", "type", "role", "href", "for", "value", "class",
]

MAX_TEXT = 200


def collect_elements(root: EnhancedDOMTreeNode, interactive_ids: set[int]) -> list[PageElement]:
    """Walk the whole page tree and list every element worth acting on.

    Listed: interactive elements, and elements that show text or have a name
    (like <span>ok</span>, which browser-use alone would skip).
    Each element gets the headings of the blocks it sits in, outermost first.
    """
    elements: list[PageElement] = []

    def visit(node: EnhancedDOMTreeNode, sections: list[str]) -> None:
        if node.node_type == NodeType.ELEMENT_NODE:
            tag = node.tag_name
            if tag in SKIPPED_BLOCKS:
                return

            heading = section_heading(node)
            if heading:
                sections = sections + [heading]

            if tag not in WRAPPER_TAGS:
                element = to_page_element(node, len(elements), sections, interactive_ids)
                if element is not None:
                    elements.append(element)

            if tag == "svg":  # an icon: list it, not its drawing parts
                return

        for child in node.children_and_shadow_roots:
            visit(child, sections)

        if node.content_document is not None:  # inside an iframe
            visit(node.content_document, sections)

    visit(root, [])
    return elements


def to_page_element(
    node: EnhancedDOMTreeNode, index: int, sections: list[str], interactive_ids: set[int]
) -> PageElement | None:
    """One DOM node -> one PageElement. None for empty wrappers (a <div> with nothing of its own)."""
    text = own_text(node)
    label = readable_label(node, text)
    interactive = node.backend_node_id in interactive_ids

    if not interactive and text is None and label is None:
        return None

    return PageElement(
        index=index,
        tag=node.tag_name,
        role=chrome_role(node),
        label=label,
        text=text,
        sections=sections,
        attributes=kept_attributes(node),
        interactive=interactive,
        visible=bool(node.is_visible),
        box=box_of(node),
        xpath=node.xpath,
        backend_node_id=node.backend_node_id,
        frame_id=node.frame_id,
    )


def own_text(node: EnhancedDOMTreeNode) -> str | None:
    """The text written directly in the element, not in its children:  <span>ok</span> -> "ok"."""
    parts = []
    for child in node.children:
        if child.node_type == NodeType.TEXT_NODE:
            parts.append(child.node_value)
    return tidy(" ".join(parts))


def readable_label(node: EnhancedDOMTreeNode, text: str | None) -> str | None:
    """What a person would call the element.

    First Chrome's accessible name: it already follows <label for>, aria-label,
    aria-labelledby, alt..., so the <select> next to "Country" is called "Country".
    Then the element's own text, then a few attributes.
    """
    ax = node.ax_node
    if ax is not None and not ax.ignored:
        name = tidy(ax.name)
        if name:
            return name

    if text:
        return text

    for attribute in ["aria-label", "placeholder", "title", "alt", "value"]:
        value = tidy(node.attributes.get(attribute))
        if value:
            return value
    return None


def section_heading(node: EnhancedDOMTreeNode) -> str | None:
    """The heading that names this block, if it is one.

        <section><h2>Employee</h2>...</section>      ->  "Employee"
        <div class="card"><h6>Employee</h6>...</div>  ->  "Employee"   (a heading as direct child)
        <nav aria-label="Main">...</nav>              ->  "Main"
    """
    if node.tag_name in HEADING_TAGS:
        return None

    container = is_container(node)
    if container:
        name = tidy(node.attributes.get("aria-label"))
        if name:
            return name

    for child in node.children:
        if is_heading(child):
            return heading_text(child)

    if container:
        heading = first_heading_inside(node, depth=3)
        if heading is not None:
            return heading_text(heading)
    return None


def is_container(node: EnhancedDOMTreeNode) -> bool:
    if node.tag_name in CONTAINER_TAGS:
        return True
    return node.attributes.get("role") in CONTAINER_ROLES


def is_heading(node: EnhancedDOMTreeNode) -> bool:
    if node.node_type != NodeType.ELEMENT_NODE:
        return False
    return node.tag_name in HEADING_TAGS or node.attributes.get("role") == "heading"


def first_heading_inside(node: EnhancedDOMTreeNode, depth: int) -> EnhancedDOMTreeNode | None:
    """The first heading in the block, looking at most `depth` levels down."""
    if depth == 0:
        return None
    for child in node.children:
        if is_heading(child):
            return child
        if child.node_type == NodeType.ELEMENT_NODE:
            found = first_heading_inside(child, depth - 1)
            if found is not None:
                return found
    return None


def heading_text(node: EnhancedDOMTreeNode) -> str | None:
    return tidy(node.get_all_children_text())


def chrome_role(node: EnhancedDOMTreeNode) -> str | None:
    if node.ax_node is None or node.ax_node.role in EMPTY_ROLES:
        return None
    return node.ax_node.role


def kept_attributes(node: EnhancedDOMTreeNode) -> dict[str, str]:
    kept = {}
    for name in KEPT_ATTRIBUTES:
        value = node.attributes.get(name)
        if value:
            kept[name] = value
    return kept


def box_of(node: EnhancedDOMTreeNode) -> Box | None:
    rect = node.absolute_position
    if rect is None:
        return None
    return Box(x=rect.x, y=rect.y, width=rect.width, height=rect.height)


def tidy(text: str | None) -> str | None:
    """Squash spaces and cut very long text. None if nothing is left."""
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    return text[:MAX_TEXT]
