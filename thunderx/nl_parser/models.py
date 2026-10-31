"""Data classes: what nl_parser takes in and gives back."""

from typing import Literal

from pydantic import BaseModel, Field

Action = Literal["click", "double_click", "right_click", "hover", "type", "select", "check", "uncheck"]
Relation = Literal["within", "near", "above", "below", "left_of", "right_of"]


class Target(BaseModel):
    """The element to act on:  "the second Save button"."""

    text: str | None = None     # what the element says: "Save"
    role: str | None = None     # what kind of element it is: "button"
    ordinal: int | None = None  # which one, if several look the same: 2 ("the last" -> -1)


class Hint(BaseModel):
    """Where the target is, relative to another element:  "under the Employee section"."""

    relation: Relation          # "within"
    text: str | None = None     # what that element says: "Employee"
    role: str | None = None     # what kind of element it is: "section"


class ParsedInstruction(BaseModel):
    raw: str
    action: Action | None = None  # None: no verb found, element_finder decides
    target: Target = Target()
    hint: Hint | None = None
    value: str | None = None      # text to type / option to pick: "john", "France"


class ParseRequest(BaseModel):
    instruction: str = Field(min_length=1, examples=["Hover over ok under Employee section"])
