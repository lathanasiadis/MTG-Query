import datetime
import os
from typing import Any

from mtgquery.constants import files, links
from mtgquery.utils import get_and_decompress, save_json_file


def filter_non_cards(oracle_cards):
    # Ignore MTG Arena cards
    # Since I'm using scryfall's "one definitive printing" data,
    # some old cards are represented by their printings in mtgo-only remaster sets like Tempest Remastered
    # So, we also need to consider mtgo here. Its fun stuff like vanguards are filtered down the line.
    filtered = filter(lambda card: "paper" in card["games"] or "mtgo" in card["games"], oracle_cards)

    # Ignore card objects that do not go into your deck
    filtered = filter(
        lambda card: card["layout"] not in [
            "planar",
            "scheme",
            "vanguard",
            "token",
            "double_faced_token",
            "emblem",
            "art_series"
        ],
        filtered)
    # some tokens have a different layout, so we need set_type to filter them out.
    filtered = filter(
        lambda card: card["set_type"] != "token",
        filtered
    )

    # Ignore playtest cards
    filtered = filter(lambda card: "playtest" not in [] if card.get("promo_types") is None else card.get("promo_types"), filtered)

    # Ignore unset cards
    filtered = filter(lambda card: card["set_type"] != "funny", filtered)

    # Ignore helper card objects for specific events/cards
    # (e.g dungeons, Theros Hero's Path)
    filtered = filter(lambda card: card["set_type"] != "memorabilia", filtered)

    return list(filtered)


def add_if_exists(original: dict[str, Any], filtered: dict[str, Any], field: str, default=None):
    """
    If field exists in the original dict, add its value to the filtered dict.
    If field does not exist and default is set, add the default value to the filtered dict.
    """
    val = original.get(field)
    if val is not None:
        filtered[field] = val
    elif default is not None:
        filtered[field] = default


def clean_card_db(original_db):
    clean_db = []
    for card in original_db:

        # Attributes present in every card
        d = {
            "name": card["name"],
            "layout": card["layout"],
            "cmc": card["cmc"],
            "color_identity": card["color_identity"],
            "keywords": card["keywords"],
            "rarity": card["rarity"],
            "oracle_tags": card["oracle_tags"],
            "type_line": card["type_line"]
        }

        # Add price attribute. Prefer EUR values over USD
        if card["prices"]["eur"] is not None:
            d["price"] = float(card["prices"]["eur"])
        elif card["prices"]["usd"] is not None:
            d["price"] = float(card["prices"]["usd"])
        elif card["prices"]["eur_foil"] is not None:
            d["price"] = float(card["prices"]["eur_foil"])
        elif card["prices"]["usd_foil"] is not None:
            d["price"] = float(card["prices"]["usd_foil"])
        else:
            d["price"] = 0.0

        # Attributes that may not exist depending
        # (e.g only creatures have power/toughness)
        for field in [
            "colors",
            "oracle_text",
            "mana_cost",
            "power",
            "toughness",
            "loyalty",
            "produced_mana",
        ]:
            add_if_exists(card, d, field)

        # EDHREC Rank can be used to sort results, so I want the field to always be present
        add_if_exists(card, d, "edhrec_rank", 99999)

        # Add card faces
        card_faces = card.get("card_faces")
        if card_faces is not None:
            d["card_faces"] = []
            for cf in card_faces:
                cur_face = {
                    "name": cf["name"],
                    "mana_cost": cf["mana_cost"],
                    "type_line": cf["type_line"],
                    "oracle_text": cf["oracle_text"]
                }
                add_if_exists(cf, cur_face, "power")
                add_if_exists(cf, cur_face, "toughness")
                add_if_exists(cf, cur_face, "color")

                d["card_faces"].append(cur_face)

        clean_db.append(d)
    return clean_db


def clean_tags_dict(d: dict[str, Any]) -> dict[str, Any]:
    """
    Given the 'oracle-tag': 'description' dictionary, remove three types of keys:
    a) tags not needed for the physical game (seek, conjure)
    b) tags unlikely to be searched ('cycles' of cards in each set which account for close to ~30% of the otags in scryfall,
    tags about creatures that have type errata)
    c) tags which which will be handled in different dicts (typal, tutor)
    """

    return {k: d[k] for k in filter(lambda x: "seek" not in x \
                                    and "conjure" not in x \
                                    and "cycle" not in x \
                                    and "type errata" not in x \
                                    and "typal" not in x \
                                    and "tutor" not in x, d)}


def create_links_dict(cards):
    """
    Create a dictionary that maps card names to scryfall links
    cards should not include tokens that have the same name as cards
    (e.g Ajani's Pridemate) because they can overwrite the link entry
    for the actual card

    Double-faced and split cards are added 3 times in the dict:
    one with their full name (X // Y) and one with X and Y both,
    allowing for easy searching.
    """
    card_links = {card["name"]: card["scryfall_uri"] for card in cards}
    # Add entries for each face of double-faced cards
    double_faced = filter(lambda x: " // " in x["name"], cards)
    for card in double_faced:
        card_name = card["name"]
        parts = card_name.split(" // ")
        card_links[parts[0]] = card_links[card_name]
        card_links[parts[1]] = card_links[card_name]

    save_json_file(card_links, files.LINKS)


def fetch_data(check_for_new=True):
    if check_for_new:
        os.makedirs(files.DATA_DIR, exist_ok=True)
        try:
            with open(files.TIMESTAMP, "r") as f:
                timestamp = f.read().strip()
                last_dl_date = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M%S")
                now = datetime.datetime.today()
                dif = now - last_dl_date
                must_download = dif.days >= 1
        except FileNotFoundError:
            must_download = True
    else:
        must_download = False

    if must_download:
        print("Downloading new card data... ")
        cards = get_and_decompress(links.ORACLE_CARDS)
        save_json_file(cards, files.ORACLE_CARDS_ALL)
        cards = filter_non_cards(cards)
        save_json_file(cards, files.ORACLE_CARDS)
        create_links_dict(cards)

        # Add empty list attribute for oracle tags; will fill later
        for card in cards:
            card["oracle_tags"] = []

        card_is_funny = {card["oracle_id"]: card["set_type"] == "funny" for card in cards}

        tags = get_and_decompress(links.ORACLE_TAGS)
        for tag in tags:
            # Remove un-set cards from taggings
            # (don't want them to show up in example cards for each tag later on)
            tag["taggings"] = list(filter(lambda t: not card_is_funny.get(t["oracle_id"]), tag["taggings"]))
        save_json_file(tags, files.ORACLE_TAGS)

        # Add every card's tags to its dict
        id_to_card = {card["oracle_id"]: card for card in cards}
        for tag in tags:
            for tagging in tag["taggings"]:
                tagged_card = id_to_card.get(tagging["oracle_id"])
                # un-set, playtest, digital-only etc cards have been removed at this point
                # and will not exist in the id_to_card dict
                if tagged_card is not None:
                    tagged_card["oracle_tags"].append(tag["label"])

        # Remove k-v pairs I don't need from the card db and save it
        clean_db = clean_card_db(cards)
        save_json_file(clean_db, files.CARDS)

        with open(files.TIMESTAMP, "w") as f:
            cur_date = datetime.datetime.today().strftime("%Y%m%d%H%M%S")
            f.write(cur_date)

        print("Done!")
    else:
        print("Up-to-date card data exists.")


if __name__ == "__main__":
    fetch_data()
