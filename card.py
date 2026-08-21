from dataclasses import asdict, dataclass, field
from typing import Literal

from constants import files
from utils import load_json_file


@dataclass
class CardFace:
    name: str
    mana_cost: str
    type_line : str
    oracle_text: str
    power: str | None = None
    toughness: str | None = None
    color: list[Literal["W", "U", "B", "R", "G"]] | None = None


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
    card_faces: list[CardFace] = field(default_factory=list)
    colors: list[Literal["W", "U", "B", "R", "G"]] | None = None
    oracle_text: str | None = None
    mana_cost: str | None = None
    power: str | None = None
    toughness: str | None = None
    loyalty: str | None = None
    produced_mana: list[Literal["W", "U", "B", "R", "G"]] | None = None

    def for_rules_prompt(self):
        data = asdict(self)

        prompt_fields = [
            "name",
            "mana_cost",
            "type_line",
            "oracle_text",
            "power",
            "toughness",
            "loyalty"
        ]

        filtered_dict = {k: v for k,v in data.items() if k in prompt_fields and (v is not None and v != [])}

        if self.card_faces != []:
            filtered_dict["card_faces"] = [{k: v for k, v in asdict(card_face).items() if v is not None} for card_face in self.card_faces]

        return filtered_dict


def load_cards() -> list[Card]:
    cards = load_json_file(files.CARDS)
    ret = []
    for card in cards:
        if card.get("card_faces") is not None:
            card_faces = [CardFace(**cf) for cf in card.pop("card_faces")]
            ret.append(Card(**card, card_faces=card_faces))
        else:
            ret.append(Card(**card))
    return ret


if __name__ == "__main__":
    cards = load_cards()
    print(len(cards))
