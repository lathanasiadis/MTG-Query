from dataclasses import dataclass, field
from typing import Optional, Literal
from collections import defaultdict
from functools import reduce

import ahocorasick

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
    card_faces: list[CardFace] = field(default_factory=list)
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


def create_automaton():
    """
    Creates an Aho-Corasick automaton that finds card names in a given text
    """
    cards = load_cards()

    # stuff we want to be able to search for
    # key: normalized value (just lowercase for now)
    # value: original value
    needles = defaultdict(list)

    for c in cards:
        needles[c.name.lower()].append(c.name)

    normal_cards = filter(lambda x: x.card_faces == [], cards)
    normal_cards = [c.name for c in normal_cards]

    # We're looking for cards named "X, Y" (e.g Jetmir, Nexus of Revels)
    # This templating is usually found in legendary creatures, hence the variable name
    # We're mapping X to the full card name, so that the user can refer to it in a more natural way
    # Some legendaries have multiple versions of themselves.
    # In this case, the list of possible full names is kept, so that it can be shown to the user for
    # disambiguation.
    for card in normal_cards:
        if "," in card:
            name = card.split(",")[0]
            needles[name.lower()].append(card)

    # Map face names of cards with multiple faces to the full, official card name
    # e.g For the card "Fire // Ice", "Fire" and "Ice" are mapped to "Fire // Ice"
    split_cards = list(filter(lambda x: x.card_faces != [], cards))
    for card in split_cards:
        needles[card.card_faces[0].name.lower()].append(card.name)
        needles[card.card_faces[1].name.lower()].append(card.name)

    # Finally, we go over every split card part and find which ones are templated like legendaries
    # We want them to be retrievable from the legend name of both parts
    # E.g for a card A, B // C, D we want it to be retrievable by A or C
    split_cards = [[c.card_faces[0].name, c.card_faces[1].name] for c in split_cards]
    split_cards = reduce(lambda x, y: x + y, split_cards, initial=[])

    for card in split_cards:
        if "," in card:
            name = card.split(",")[0]
            needles[name].append(card)
    
    automaton = ahocorasick.Automaton()
    for k,v in needles.items():
        key = k.lower()
        val = v[0] if len(v) == 1 else v
        automaton.add_word(key, (len(key), val))
    automaton.make_automaton()

    return automaton


if __name__ == "__main__":
    load_cards()

