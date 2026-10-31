"""Core logic: read one instruction into action, target, hint and value.

    "Hover over ok under Employee section"
      -> action=hover · target "ok" · hint within "Employee" (section)

Rules only, no AI (design rule 2: cheapest method first).

The four steps run left to right on the sentence:

    "type   john   into the Email field   under   the Login section"
     action value        target             hint
"""

from thunderx.nl_parser import helpers as h
from thunderx.nl_parser.helpers import Sentence
from thunderx.nl_parser.models import Action, Hint, ParsedInstruction, Target


def parse(instruction: str) -> ParsedInstruction:
    """Split an instruction into action, target, hint and value. Never raises on odd input."""
    sentence = h.normalize(instruction)

    # Each step takes what it understands from the sentence
    # and hands the rest on to the next step.
    action, rest = read_action(sentence)
    value, rest = read_value(action, rest)
    rest, hint = read_hint(rest)
    target = read_target(rest)

    return ParsedInstruction(raw=instruction, action=action, target=target, hint=hint, value=value)


def read_action(sentence: Sentence) -> tuple[Action | None, Sentence]:
    """Read the verb at the start.

        "hover over ok under Employee section"  ->  "hover",  "ok under Employee section"
    """
    for action, pattern in h.VERB_PATTERNS:
        match = pattern.match(sentence.folded)
        if match:
            rest = sentence.part(match.end())
            return action, rest
    return None, sentence


def read_value(action: Action | None, rest: Sentence) -> tuple[str | None, Sentence]:
    """Read the text to type or the option to pick. Only "type" and "select" have one."""
    if action not in ("type", "select"):
        return None, rest

    # "fill the Email field WITH john"
    match = h.WITH_PATTERN.search(rest.folded)
    if match:
        value = rest.part(match.end()).original.strip()
        rest = rest.part(0, match.start())
        return value, rest

    # "type john INTO the Email field",  "choose France FROM the dropdown"
    match = h.VALUE_SEPARATOR_PATTERN.search(rest.folded)
    if match:
        before = rest.part(0, match.start())
        role, _ = h.remove_first_match(before, h.ROLE_PATTERNS)
        # "select the dropdown IN the form": "the dropdown" is an element, not a value
        if not before.is_empty() and role is None:
            value = before.original.strip()
            rest = rest.part(match.end())
            return value, rest

    # "type hello"  ->  into whatever field has focus
    if action == "type" and not rest.is_empty():
        value = rest.original.strip()
        return value, h.EMPTY

    return None, rest


def read_hint(rest: Sentence) -> tuple[Sentence, Hint | None]:
    """Cut the sentence at the first relation word ("under", "next to"...).

        "team section under the login button"
         target        ^ relation  anchor     ->  "team section",  Hint(below, "login", "button")
    """
    found = first_relation(rest)
    if found is None:
        return rest, None
    relation, match = found

    before = rest.part(0, match.start())   # the target
    after = rest.part(match.end())         # the anchor

    role, after = h.remove_first_match(after, h.ROLE_PATTERNS)
    text = h.leftover_words(after)

    # "click log in": nothing follows "in", so it wasn't a relation word after all
    if text is None and role is None:
        return rest, None

    if relation == "under":
        relation = meaning_of_under(role)

    hint = Hint(relation=relation, text=text, role=role)
    return before, hint


def meaning_of_under(role: str | None) -> str:
    """ "under" means inside a container, but below a single element.

        "ok under the Employee section"    ->  within
        "team section under the login button"  ->  below
    """
    if role is None or role in h.CONTAINERS:
        return "within"
    return "below"


def read_target(rest: Sentence) -> Target:
    """Read the element to act on: its text, its role ("button") and its position ("second").

        "the second Save button"  ->  Target(text="Save", role="button", ordinal=2)
    """
    role, rest = h.remove_first_match(rest, h.ROLE_PATTERNS)
    ordinal, rest = h.remove_first_match(rest, h.ORDINAL_PATTERNS)
    text = h.leftover_words(rest)
    return Target(text=text, role=role, ordinal=ordinal)


def first_relation(sentence: Sentence):
    """Find the relation word that comes first in the sentence.

    Returns (relation, match), or None if there is none.
    If two start at the same place, the longer one wins ("inside of" over "in").
    """
    best = None
    for relation, pattern in h.RELATION_PATTERNS:
        match = pattern.search(sentence.folded)
        if match is None:
            continue
        if best is None:
            best = (relation, match)
            continue

        best_match = best[1]
        starts_earlier = match.start() < best_match.start()
        same_start_but_longer = match.start() == best_match.start() and match.end() > best_match.end()
        if starts_earlier or same_start_but_longer:
            best = (relation, match)
    return best
