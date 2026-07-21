import json
import requests
import datetime
import os
import gzip

from constants import Constants as C
import data

def load_json_file(filename):
    with open(filename, "r") as f:
        return json.load(f)

def add_if_exists(original: dict, filtered: dict, field: str, default=None):
    val = original.get(field)
    if val is not None:
        filtered[field] = val
    elif default is not None:
        filtered[field] = default

def get_and_decompress(link):
    headers = {"User-Agent": "MTG Query 0.1"}

    # Fetch download link, then download the actual data
    r = requests.get(link, headers=headers)
    r = requests.get(r.json()["jsonl_download_uri"], headers=headers)

    # Decompress and decode
    content = gzip.decompress(r.content).decode()

    # Convert from JSON Lines to List of JSON
    return [json.loads(line) for line in content.split("\n")[:-1]]

def clean_card_db(original_db):
    clean_db = []
    for card in original_db:
        # Ignore digital-only cards
        if "paper" not in card["games"]:
            continue
    
        # Ignore card objects that do not go into your deck
        layout = card["layout"]
        if layout in ["planar", "scheme", "vanguard", "token", "double_faced_token", "emblem", "art_series"]:
            continue
    
        # Ignore playtest cards
        promo_types = card.get("promo_types")
        if promo_types is not None and "playtest" in promo_types:
            continue
    
        # Ignore unset cards
        if card["set_type"] == "funny":
            continue
    
        # Ignore helper card objects for specific events/cards
        # (e.g dungeons, Theros Hero's Path)
        if card["set_type"] == "memorabilia":
            continue
   
        # Attributes present in every card
        d = {
            "name": card["name"],
            "layout": card["layout"],
            "cmc": card["cmc"],
            "color_identity": card["color_identity"],
            "keywords": card["keywords"],
            "rarity": card["rarity"],
            "oracle_tags": card["oracle_tags"]
        }
        # Split type line to types and subtypes
        typeline_parts = card["type_line"].split(" — ")
        d["type"] = typeline_parts[0].split(" ")
        d["subtype"] = typeline_parts[1].split(" ") if len(typeline_parts) > 1 else []
    
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
    
        # EDHREC Rank is used to sort results, so I want the field to always be present
        add_if_exists(card, d, "edhrec_rank", 99999)
    
        # Add card faces
        card_faces = card.get("card_faces")
        if card_faces is not None:
            d["card_faces"] = []
            for cf in card_faces:
                cur_face = {
                    "name": cf["name"],
                    "mana_cost": cf["mana_cost"],
                    "oracle_text": cf["oracle_text"]
                }
                add_if_exists(cf, cur_face, "power")
                add_if_exists(cf, cur_face, "toughness")
                add_if_exists(cf, cur_face, "color")
    
                d["card_faces"].append(cur_face)
        
        clean_db.append(d)
    return clean_db

def label_descendants(label, descendant_tag, tag_id_lookup):
    parent_labels = descendant_tag.get("parent_labels")
    if parent_labels is None:
        descendant_tag["parent_labels"] = [label]
        #print(f'Addint parent labels to {descendant_tag["label"]}')
    else:
        parent_labels.append(label)

    for child_id in descendant_tag["child_ids"]:
        child_tag = tag_id_lookup[child_id]
        label_descendants(label, child_tag, tag_id_lookup)


def flatten_tag_hierarchy(tags):
    tag_id_lookup = {t["id"]: t for t in tags}
    for tag in tags:
        for child_id in tag["child_ids"]:
            child_tag = tag_id_lookup[child_id]
            label_descendants(tag["label"], child_tag, tag_id_lookup)
            #print(f'after label desc: {child_tag["parent_labels"]}') 


def clean_tags_dict(d: dict) -> dict:
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
def get_prefix_tags(d: dict, prefix: str) -> dict:
    """
    Given a dictionary, return a dictionary with only the keys that contain prefix
    """
    return {k: d[k] for k in filter(lambda x: prefix in x, d)}

class TreeNode:
    def __init__(self, label):
        self.label = label
        self.children = []

class TagTree:
    def __init__(self, otags):
        self.root_nodes = []
        self.name_to_id = {t["label"]: t["id"] for t in otags}
        # First pass: create a TreeNode for every tag        
        self.id_to_node = {t["id"]: TreeNode(t["label"]) for t in otags}

        # Second pass: add each tag's children to its TreeNode as TreeNodes themselves
        # Also, create a list of every parentless node (root nodes)
        for tag in otags:
            tag_node = self.id_to_node[tag["id"]]
            tag_node.children = [self.id_to_node[child_id] for child_id in tag["child_ids"]]
            if tag["parent_ids"] == []:
                self.root_nodes.append(tag_node)

    def get_children(self, label):
        child_id = self.name_to_id[label]
        return [c.label for c in self.id_to_node[child_id].children]

def fetch_data():
    os.makedirs(C.DATA_DIR, exist_ok=True)
   
    try:
        with open(C.FILES["DL_TIMESTAMP"], "r") as f:
            timestamp = f.read().strip()
            last_dl_date = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M%S")
            now = datetime.datetime.today()
            dif = now - last_dl_date
            must_download = dif.days >= 1
    except FileNotFoundError:
        must_download = True

    if must_download:
        print("Downloading new card data... ")
        cards = get_and_decompress(C.LINKS["CARDS"])
        with open(C.ORACLE["CARDS"], "w") as f:
            json.dump(cards, f)    

        # Add empty list attribute for oracle tags; will fill later
        for card in cards:
            card["oracle_tags"] = []

        # Create a dictionary that maps card names to scryfall links
        card_links = {card["name"]: card["scryfall_uri"] for card in cards}
        # Add entries for each face of double-faced cards
        double_faced = filter(lambda x: " // " in x["name"], cards)
        for card in double_faced:
            card_name = card["name"]
            parts = card_name.split(" // ")
            card_links[parts[0]] = card_links[card_name]
            card_links[parts[1]] = card_links[card_name]

        with open(C.FILES["LINKS"], "w") as f:
            json.dump(card_links, f)

        tags = get_and_decompress(C.LINKS["TAGS"])
        #flatten_tag_hierarchy(tags)
        with open(C.ORACLE["TAGS"], "w") as f:
            json.dump(tags, f)

        tag_descriptions = {}
        tagged_cards = {}
        
        for tag in tags:
            desc = tag["description"]
            tag_descriptions[tag["label"]] = desc.lower() if desc is not None else None
            for tagging in tag["taggings"]:
                o_id = tagging["oracle_id"]

                if tagged_cards.get(o_id) is None:
                    tagged_cards[o_id] = {tag["label"]}
                else:
                    tagged_cards[o_id].update([tag["label"]])
                
                #parent_labels = tag.get("parent_labels")
                #if parent_labels is not None:
                    #tagged_cards[o_id].update(parent_labels)

        for card in cards:
            o_tags = tagged_cards.get(card["oracle_id"])
            if o_tags is not None:
                card["oracle_tags"] = list(o_tags)

        clean_db = clean_card_db(cards)

        with open(C.FILES["TAGS_ALL"], "w") as f:
            json.dump(tag_descriptions, f)

        tags_filtered = clean_tags_dict(tag_descriptions)
        with open(C.FILES["TAGS"], "w") as f:
            json.dump(tags_filtered, f)

        tags_typal = get_prefix_tags(tag_descriptions, "typal")
        with open(C.FILES["TAGS_TYPAL"], "w") as f:
            json.dump(tags_typal, f)  
        
        tags_tutor = get_prefix_tags(tag_descriptions, "tutor")
        with open(C.FILES["TAGS_TUTOR"], "w") as f:
            json.dump(tags_tutor, f)

        with open(C.FILES["CARDS"], "w") as f:
            json.dump(clean_db, f)
        
        with open(C.FILES["DL_TIMESTAMP"], "w") as f:
            cur_date = datetime.datetime.today().strftime("%Y%m%d%H%M%S")
            f.write(cur_date)
       
        print("Done!")
    else:
        print("Up-to-date card data exists.")

def load_data():
    data.DB = load_json_file(C.FILES["CARDS"])
    # Right now, using the tag names without their descriptions.
    # They seem to not be essential, and this way the agent requires less tokens.
    data.TAGS = load_json_file(C.FILES["TAGS"]).keys()
    data.TAG_TREE = TagTree(load_json_file(C.ORACLE["TAGS"]))
    data.TAGS_TUTOR = load_json_file(C.FILES["TAGS_TUTOR"]).keys()
    data.TAGS_TYPAL = load_json_file(C.FILES["TAGS_TYPAL"]).keys()

    data.CARD_LINKS = load_json_file(C.FILES["LINKS"])

if __name__ == "__main__":
    fetch_data()
