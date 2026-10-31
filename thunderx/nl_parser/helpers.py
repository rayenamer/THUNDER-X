"""Vocabulary and text helpers. No parsing decisions here, see services.py for those.

Every table is (name, regex on folded text: lowercase, no accents), English and French.
Order matters: longer phrases first ("double click" before "click").
"""

import re
import unicodedata
from dataclasses import dataclass

from thunderx.nl_parser.models import Action

# ── vocabulary ──────────────────────────────────────────────────────────────

VERBS: list[tuple[Action, str]] = [
    ("double_click", r"double[- ]?click(?:\s+on)?|double[- ]?cliqu\w*(?:\s+sur)?"),
    ("right_click", r"right[- ]?click(?:\s+on)?|clic\s+droit(?:\s+sur)?"),
    ("hover", r"hover(?:\s+(?:over|on))?|mouse\s*over|move\s+(?:the\s+)?mouse\s+(?:over|to)"
              r"|survol\w*|passe[rz]?\s+la\s+souris\s+sur"),
    ("uncheck", r"uncheck|untick|decoch\w*"),
    ("check", r"check|tick|coch\w*"),
    ("type", r"type|enter|input|write|fill(?:\s+in)?|saisi\w*|tape[rz]?|entre[rz]?|ecri\w*|rempli\w*|renseign\w*"),
    ("select", r"select|choose|pick|selectionn\w*|choisi\w*"),
    ("click", r"click(?:\s+on)?|press|tap|push|hit|open|cliqu\w*(?:\s+sur)?|clic\s+sur|appuy\w*(?:\s+sur)?"),
]

_FR_DE = r"\s+d(?:e|u|es)"  # "à côté de / du / des"

# "under" is not a final relation: services.py turns it into "within" or "below",
# depending on the element it points to.
RELATIONS: list[tuple[str, str]] = [
    ("near", rf"next\s+to|beside|near(?:\s+to)?|close\s+to|a\s+cote{_FR_DE}|pres{_FR_DE}|aupres{_FR_DE}"),
    ("left_of", rf"(?:to\s+the\s+)?left\s+of|a\s+gauche{_FR_DE}"),
    ("right_of", rf"(?:to\s+the\s+)?right\s+of|a\s+droite{_FR_DE}"),
    ("above", rf"above|on\s+top\s+of|au[- ]dessus{_FR_DE}"),
    ("below", rf"below|beneath|underneath|(?:en|au)[- ]dessous{_FR_DE}"),
    ("under", r"under|sous"),
    ("within", r"inside(?:\s+of)?|within|in|from|dans|parmi"),
]

# Element types, shared by the target ("the Save BUTTON") and the hint ("under the Employee SECTION").
ROLES: list[tuple[str, str]] = [
    # single elements
    ("radio", r"radio\s+button|bouton\s+radio|radio"),
    ("checkbox", r"check\s*box|tick\s*box|case\s+a\s+cocher|case"),
    ("dropdown", r"drop[- ]?down|select\s*box|combo\s*box|picklist|liste\s+deroulante|menu\s+deroulant|select"),
    ("textbox", r"text\s*box|text\s+field|text\s*area|input\s+field|search\s+box|input|field"
                r"|zone\s+de\s+texte|champ\s+de\s+saisie|champ"),
    ("button", r"button|btn|bouton"),
    ("link", r"hyperlink|link|lien"),
    ("tab", r"tab|onglet"),
    ("icon", r"icon|icone"),
    ("image", r"image|img|picture|photo|logo"),
    ("option", r"option|choice"),
    ("switch", r"toggle|switch|interrupteur"),
    ("label", r"label|libelle"),
    ("heading", r"heading|title|titre"),
    # containers: elements that hold other elements
    ("section", r"section"),
    ("form", r"form|formulaire"),
    ("dialog", r"dialog|modal|pop[- ]?up|boite\s+de\s+dialogue|fenetre"),
    ("table", r"table|tableau"),
    ("row", r"row|ligne"),
    ("column", r"column|colonne"),
    ("card", r"card|carte"),
    ("header", r"header|en[- ]?tete"),
    ("footer", r"footer|pied\s+de\s+page"),
    ("sidebar", r"side\s*bar|barre\s+laterale"),
    ("nav", r"nav\s*bar|navigation|nav"),
    ("menu", r"menu"),
    ("panel", r"panel|panneau"),
    ("list", r"list|liste"),
    ("area", r"area|zone|block|bloc"),
]

CONTAINERS = {
    "section", "form", "dialog", "table", "row", "column", "card", "header",
    "footer", "sidebar", "nav", "menu", "panel", "list", "area",
}

ORDINALS: list[tuple[int, str]] = [
    (1, r"first|1st|premier|premiere"),
    (2, r"second|2nd|deuxieme|seconde"),
    (3, r"third|3rd|troisieme"),
    (4, r"fourth|4th|quatrieme"),
    (5, r"fifth|5th|cinquieme"),
    (-1, r"last|dernier|derniere"),
]

# Words between a value and its field: "type john INTO the Email field", "choose France FROM ...".
VALUE_SEPARATORS = r"into|inside|in|onto|on|from|dans|sur|depuis|en"

# Filler words dropped at the edges of a text: "the Save" -> "Save".
# Only at the edges, so "Se souvenir de moi" keeps its "de".
STOPWORDS = {
    "the", "a", "an", "on", "to", "at", "this", "that", "which", "says", "say", "with", "text",
    "labelled", "labeled", "called", "named", "titled", "marked", "element", "item", "one",
    "le", "la", "les", "un", "une", "des", "du", "de", "sur", "au", "aux",
    "qui", "dit", "élément", "intitulé", "nommé", "appelé",
}

# Polite words at the start that we skip: "please click ..." reads as "click ...".
POLITE_WORDS = ["please", "pls", "now", "then", "and", "veuillez", "merci de", "s'il vous plait"]


# ── compiled patterns ───────────────────────────────────────────────────────

def compile_table(table: list, at_start: bool = False) -> list:
    """Turn [(name, "word|other word"), ...] into [(name, regex), ...].

    Each regex matches whole words only ("tab" won't match inside "table")
    and also eats the spaces after them.
    at_start=True: the words must be at the very start of the text (used for verbs).
    """
    start = "^" if at_start else r"\b"
    compiled = []
    for name, words in table:
        regex = re.compile(start + "(?:" + words + r")\b\s*")
        compiled.append((name, regex))
    return compiled


VERB_PATTERNS = compile_table(VERBS, at_start=True)
RELATION_PATTERNS = compile_table(RELATIONS)
ROLE_PATTERNS = compile_table(ROLES)
ORDINAL_PATTERNS = compile_table(ORDINALS)

# "fill the Email field WITH john"
WITH_PATTERN = re.compile(r"\b(?:with|avec)\s+(?=\S)")

# "type john INTO the Email field"
VALUE_SEPARATOR_PATTERN = re.compile(r"\b(?:" + VALUE_SEPARATORS + r")\b\s*")

POLITE_START = re.compile(r"^(?:(?:" + "|".join(POLITE_WORDS) + r")\s+)+")

# Quote marks around words ("Save", 'Save', «Save»), but not the ' inside l'employé.
QUOTE_MARKS = re.compile(r"[\"“”«»]|(?<!\w)'|'(?!\w)")


# ── the sentence ────────────────────────────────────────────────────────────

@dataclass
class Sentence:
    """The instruction twice: as the user typed it, and folded for matching.

        original: "Survoler ok sous la section Employé"
        folded:   "survoler ok sous la section employe"

    Both always have the same length, so a position found in `folded`
    points to the same words in `original`. We search in `folded`
    and give back words from `original`, with the user's spelling.
    """

    original: str
    folded: str

    def part(self, start: int = 0, end: int | None = None) -> "Sentence":
        """A slice of the sentence, like text[start:end]."""
        return Sentence(self.original[start:end], self.folded[start:end])

    def without(self, match: re.Match) -> "Sentence":
        """The sentence with a found word cut out."""
        before = self.part(0, match.start())
        after = self.part(match.end())
        return Sentence(before.original + " " + after.original, before.folded + " " + after.folded)

    def is_empty(self) -> bool:
        return self.folded.strip() == ""


EMPTY = Sentence("", "")


# ── text helpers ────────────────────────────────────────────────────────────

def fold(text: str) -> str:
    """Lowercase and remove accents, one character for one character:  "Sélectionner" -> "selectionner"."""
    letters = []
    for char in text:
        base_letter = unicodedata.normalize("NFKD", char)[0]  # "é" -> "e"
        letters.append(base_letter.lower()[0])
    return "".join(letters)


def normalize(instruction: str) -> Sentence:
    """Clean the instruction:  "Please  click on "About us"."  ->  "click on About us"."""
    text = instruction.replace("’", "'").replace("‘", "'")  # curly apostrophes -> '
    text = QUOTE_MARKS.sub(" ", text)       # quote marks are ignored
    text = re.sub(r"\s+", " ", text)        # many spaces -> one
    text = text.strip(" .!?;:,")            # punctuation at the ends
    sentence = Sentence(original=text, folded=fold(text))

    polite = POLITE_START.match(sentence.folded)  # "please click" -> "click"
    if polite:
        sentence = sentence.part(polite.end())
    return sentence


def remove_first_match(sentence: Sentence, table: list) -> tuple:
    """Find the first table entry in the sentence; return its name and the sentence without it.

        "the second button", ROLE_PATTERNS  ->  "button",  "the second "
    """
    for name, regex in table:
        match = regex.search(sentence.folded)
        if match:
            return name, sentence.without(match)
    return None, sentence


def leftover_words(sentence: Sentence) -> str | None:
    """The words that still mean something, as the user typed them.

        "the  Save "  ->  "Save"          "la  de l'employé"  ->  "employé"

    None if nothing is left.
    """
    words = []
    for match in re.finditer(r"[\w'@.-]+", sentence.original):
        word = match.group()
        if word[:2].lower() in ("l'", "d'"):  # French "l'employé" -> "employé"
            word = word[2:]
        if word:
            words.append(word)

    while words and words[0].lower() in STOPWORDS:   # filler at the start
        words.pop(0)
    while words and words[-1].lower() in STOPWORDS:  # filler at the end
        words.pop()

    if not words:
        return None
    return " ".join(words)


# ── comparing texts (used by element_finder) ────────────────────────────────

def simplify(text: str | None) -> str:
    """Text reduced to what matters for comparing:  "  Save *"  ->  "save",  "Employé:"  ->  "employe"."""
    if not text:
        return ""
    text = fold(text)
    text = re.sub(r"[^\w]+", " ", text)  # punctuation and symbols -> spaces
    return " ".join(text.split())


def same_text(a: str | None, b: str | None) -> bool:
    """ "About us" == "about  US" == "About us:". Empty text never matches."""
    a = simplify(a)
    return a != "" and a == simplify(b)


def contains_words(longer: str | None, words: str | None) -> bool:
    """ "Employee Information" contains "employee". Whole words only: "Employees" doesn't."""
    words = simplify(words)
    if words == "":
        return False
    return f" {words} " in f" {simplify(longer)} "
