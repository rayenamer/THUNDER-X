"""Write our elements in the exact format Quantum08/laya-browser-mind2web was trained on.

Copied from jev_ultrafast (formatter.py and shortlister.py, github.com/HiteshS08/laya-system-use).
The model card says the shortlist and the way options are written are part of the model:
change them and its scores don't hold. So they stay identical here.
"""

import re
import unicodedata
from collections import Counter

from thunderx.page_extractor.models import PageElement

SHORTLIST_SIZE = 20   # what fits in the model's context
MAX_LABEL_CHARS = 70
MAX_VALUE_CHARS = 20

# Our action -> the operation the model knows. It was never trained on hover: closest is CLICK.
OPERATIONS = {
    "click": "CLICK", "double_click": "CLICK", "right_click": "CLICK", "hover": "CLICK",
    "check": "CLICK", "uncheck": "CLICK",
    "type": "TYPE_TEXT",
    "select": "SELECT",
}

# Laya doesn't see the question's name, so the instruction says what the options are for.
TARGET_INSTRUCTIONS = {
    "CLICK": "Which element should be clicked next to advance the goal?",
    "TYPE_TEXT": "Which field should be typed into next to advance the goal?",
    "SELECT": "Which dropdown should be set next to advance the goal?",
}


# ── the request ─────────────────────────────────────────────────────────────

def operation_of(action: str | None) -> str:
    return OPERATIONS.get(action, "CLICK")


def question_name(operation: str) -> str:
    """ "CLICK" -> "click_target"."""
    return f"{operation.lower()}_target"


def option_id(element: PageElement) -> str:
    return f"e{element.index}"


def build_request(goal: str, operation: str, elements: list[PageElement]) -> dict:
    """The body of POST /v1/systemone: the goal, and one question whose options are the elements.

        {"state": {"goal": "click on button inspirations", "recent_actions": []},
         "questions": {"click_target": {"type": "choice",
                                        "instructions": "Which element should be clicked next...",
                                        "criteria": {"e12": "Inspirations (link)", ...}}}}
    """
    options = {}
    for element in elements:
        options[option_id(element)] = render_option(element)

    return {
        "model": "english",  # the fine-tune is served under this name (docker-compose.yml)
        "state": {"goal": goal, "recent_actions": []},
        "questions": {
            question_name(operation): {
                "type": "choice",
                "instructions": TARGET_INSTRUCTIONS[operation],
                "criteria": options,
            }
        },
    }


def render_option(element: PageElement) -> str:
    """One element as one option:  "Search packages (searchbox, =json)",  "Inspirations (link)"."""
    label = clip(candidate_label(element), MAX_LABEL_CHARS) or element.role or "unnamed"

    extras = []
    if element.role:
        extras.append(element.role)
    value = clip(element.attributes.get("value", ""), MAX_VALUE_CHARS)
    if value:
        extras.append(f"={value}")

    if extras:
        return f"{label} ({', '.join(extras)})"
    return label


def candidate_label(element: PageElement) -> str:
    """Same order as training: aria-label, text, alt, title, placeholder, value, name.

    Our `label` is Chrome's accessible name, which already follows aria-label and the text,
    so it comes first, then the attributes.
    """
    if element.label:
        return element.label
    for attribute in ["aria-label", "alt", "title", "placeholder", "value", "name"]:
        value = element.attributes.get(attribute)
        if value:
            return value
    return ""


def clip(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit]


# ── the shortlist ───────────────────────────────────────────────────────────

# Words that would match every label: "click" is in the goal, not on the page.
QUERY_STOPWORDS = {"click", "type", "text", "select", "the", "and", "for", "with", "from", "that", "this"}

# Small bonus by role for elements no word matches (measured on Mind2Web: fields are likelier targets).
ROLE_PRIOR = {
    "textbox": 1.0, "searchbox": 1.0, "combobox": 1.0,
    "button": 0.5, "option": 0.5, "tab": 0.5, "checkbox": 0.5, "spinbutton": 0.5, "switch": 0.5,
}
ROLE_WEIGHT = 0.4
POSITION_WEIGHT = 0.3  # earlier on the page is likelier


def shortlist(goal: str, elements: list[PageElement], size: int = SHORTLIST_SIZE) -> list[PageElement]:
    """The `size` elements most related to the goal, kept in page order."""
    if len(elements) <= size:
        return list(elements)

    texts = []
    for element in elements:
        texts.append(f"{candidate_label(element)} {element.attributes.get('value', '')}")

    query = word_set(goal) - QUERY_STOPWORDS
    words = [word_set(text) for text in texts]
    lengths = [len(tokens(text)) for text in texts]

    # How many elements carry each word: rare words weigh more.
    how_many_have = Counter()
    for element_words in words:
        how_many_have.update(element_words)

    average_length = sum(lengths) / len(lengths) if lengths else 1.0
    last = max(len(elements) - 1, 1)

    scores = []
    for i, element in enumerate(elements):
        word_match = 0.0
        for word in words[i] & query:
            word_match += 1.0 / how_many_have[word]
        word_match *= average_length / max(lengths[i], 1)  # a match in a short label beats one in a long label

        role_bonus = ROLE_WEIGHT * ROLE_PRIOR.get(element.role, 0.0)
        position_bonus = POSITION_WEIGHT * (1.0 - i / last)
        scores.append(word_match + role_bonus + position_bonus)

    best_first = sorted(range(len(elements)), key=lambda i: (-scores[i], i))
    kept = sorted(best_first[:size])  # back to page order
    return [elements[i] for i in kept]


def tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]{2,}", folded)


def word_set(text: str) -> set[str]:
    """Words of 2+ letters, plural "s" dropped:  "Hotels in Tunisia" -> {"hotel", "in", "tunisia"}."""
    words = set()
    for word in tokens(text):
        if len(word) > 3 and word.endswith("s"):
            word = word[:-1]
        words.add(word)
    return words
