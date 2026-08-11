from dataclasses import dataclass, field
from typing import Optional, Literal
from utils import load_json_file
from constants import Constants as C

@dataclass
class CardFace:
    name: str
    mana_cost: str
    type_line : str
    oracle_text: str
    power: Optional[str] = None
    toughness: Optional[str] = None
    color: Optional[list[Literal["W", "U", "B", "R", "G"]]] = None


@dataclass
class Card:
    name: str
    layout: str
    cmc: int
    color_identity: list[Literal["W", "U", "B", "R", "G"]]
    keywords: list[str]
    rarity: list[Literal["common", "uncommon", "rare", "mythic"]]
    oracle_tags: list[str]
    type_line: str
    price: float
    edhrec_rank: int
    card_faces: Optional[list[CardFace]] = field(default_factory=list)
    colors: Optional[list[Literal["W", "U", "B", "R", "G"]]] = None
    oracle_text: Optional[str] = None
    mana_cost: Optional[str] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    produced_mana: Optional[list[Literal["W", "U", "B", "R", "G"]]] = None


def load_cards() -> list[Card]:
    cards = load_json_file(C.FILES["CARDS"])
    ret = []
    for card in cards:
        if card.get("card_faces") is not None:
            card_faces = [CardFace(**cf) for cf in card.pop("card_faces")]
            ret.append(Card(**card, card_faces=card_faces))
        else:
            ret.append(Card(**card))
    return ret


if __name__ == "__main__":
    load_cards()

