from __future__ import annotations

from typing import Literal

from card import Card
from data import State


def find_card(name: str) -> Card | None:
    """
    Returns details on the Magic card named name
    """
    for card in State.cards:
        if card.name == name:
            return card
    return None


def retrieve(query: str, corpus: Literal["rules", "qa"], k: int = 3):
    query = "Represent this sentence for searching relevant passages: " + query
    store = State.rules_store if corpus == "rules" else State.qa_store
    results = store.similarity_search(query, k=k)
    return [res.metadata["source"] for res in results]
