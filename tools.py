from __future__ import annotations
from operator import itemgetter
from typing import Annotated, Union, Literal, List
from functools import reduce

from pydantic import BaseModel, Field
from langchain.tools import tool
import Levenshtein

from fetch_data import load_data
import data

class ArithmeticFilter(BaseModel):
    kind: Literal["arithmetic"] = "arithmetic"
    field: Literal["cmc", "price"]
    op: Literal["<", "<=", "=", ">=", ">"]
    value: int | float = Field(
            description = "Use int when comparing cmc and float when comparing prices. Prices are stored in EUR."
    )

class ColorFilter(BaseModel):
    kind: Literal["color_identity"] = "color_identity"
    op: Literal["<=", "=", ">="]
    value: List[Literal["W", "U", "B", "R", "G"]]

class RarityFilter(BaseModel):
    kind: Literal["rarity"] = "rarity"
    op: Literal["="]
    value: Literal["common", "uncommon", "rare", "mythic"]

class TagFilter(BaseModel):
    kind: Literal["oracle_tags"] = "oracle_tags"
    value: str
    op: Literal["in"] = "in"

class TypeFilter(BaseModel):
    """
    This filter allows you to search for cards matching a specific type.
    A card may have multiple types.
    Supertypes are also included in this filter.
    To search for a card that matches two types at the same, use AndFilter.
    For example, AndFilter(value=[TypeFilter(value="World"), TypeFilter(value="Enchantment")])
    will find World Enchantments.
    """

    kind: Literal["type"] = "type"
    op: Literal["in"]
    value: Literal[
        # Supertypes
        "Basic",
        "Legendary",
        "Snow",
        "World",
        # Types
        "Land",
        "Creature",
        "Artifact",
        "Enchantment",
        "Planeswalker",
        "Battle",
        "Instant",
        "Sorcery",
        "Kindred"
    ]

class SubtypeFilter(BaseModel):
    kind: Literal["subtype"] = "subtype"
    op: Literal["in"]
    value: str

class NameFilter(BaseModel):
    kind: Literal["name"] = "name"
    op: Literal["="]
    value: str

class AndFilter(BaseModel):
    kind: Literal["and"] = "and"
    value: List[Filter]

class OrFilter(BaseModel):
    kind: Literal["or"] = "or"
    value: List[Filter]

Filter = Annotated[
    ArithmeticFilter
    | ColorFilter
    | RarityFilter
    | TagFilter
    | TypeFilter
    | SubtypeFilter
    | NameFilter
    | AndFilter
    | OrFilter,
    Field(discriminator="kind")
]

AndFilter.model_rebuild()
OrFilter.model_rebuild()

class QueryInput(BaseModel):
    filters: AndFilter | OrFilter = Field(
            description="Use AndFilter to chain together filters with a logical AND, and OrFilter for the logical OR, respectively. You can nest them!"
    )

class TagSearchInput(BaseModel):
    keywords: List[str]

class NameSearchInput(BaseModel):
    name: str

class LinkFetchInput(BaseModel):
    card_names: List[str]

def has_one_of_op(x: List[str], y: List[str]) -> bool:
    found = False
    for x_item in x:
        if x_item in y:
            found = True
            break
    return found

OP_DICT = {
    "=": lambda x,y: x == y,
    ">": lambda x,y: x > y,
    ">=": lambda x,y: x >= y,
    "<": lambda x,y: x < y,
    "<=": lambda x,y: x <= y,
    "contains": lambda x,y: set(y).issubset(x),
    "in": lambda x,y: y in x,
    "has_one_of_op": has_one_of_op
}

COLOR_OP_DICT = {
    "<=": lambda x,y: set(y).issubset(set(x)),
    "=": lambda x,y: set(x) == set(y),
    ">=": lambda x,y: set(y).issuperset(set(x))
}

@tool
def get_tags():
    """
    Returns a list containing every generic tag
    """
    return data.TAGS

@tool
def get_typal_tags():
    """
    Returns a list containing every oracle tag referencing typals.
    Use this ONLY to find tags for typal/tribal/kindred synergies (i.e synergies with specific creature types)
    or for their hate versions (i.e negative effects to specific creature types).
    """
    return data.TAGS_TYPAL

@tool
def get_tutor_tags():
    """
    Returns a list containing every oracle tag referencing tutors (i.e cards that search for other cards).
    Use this ONLY to find tags for searching for specific cards.
    """
    return data.TAGS_TUTOR

@tool
def get_root_tags():
    """
    Returns a list of every root tag, i.e a tag without parents.
    """
    return [n.label for n in data.TAG_TREE.root_nodes]

@tool
def get_tag_children(tag: str):
    """
    Returns a list of children tags for a given tag.
    Children tags are specialized versions of the parent effect.
    For example, the tag 'removal' has the children 'removal-creature' and 'removal-artifact', besides others.
    """
    tag_id = data.TAG_TREE.name_to_id[tag]
    return [n.label for n in data.TAG_TREE.id_to_node[tag_id].children]

def get_tag_descendants(tag: str):
    tag_id = data.TAG_TREE.name_to_id[tag]
    descendants = []

    for child in data.TAG_TREE.id_to_node[tag_id].children:
        descendants.append(child.label)
        descendants += get_tag_descendants(child.label)

    return descendants

@tool(args_schema=TagSearchInput)
def search_tags(keywords):
    """
    Returns the tag names that contain a set of keywords.
    Tag descriptions are also searched, for tags that contain one.
    """
    ret = set()

    for k,v in data.TAGS.items():
        key_matched = False
        for keyword in keywords:
            if keyword in k:
                key_matched = True
                break

        if key_matched:
            ret.add(k)

        if v is None:
            continue

        val_matched = False
        for keyword in keywords:
            if keyword in v:
                val_matched = True
                break
        if val_matched:
            ret.add(k)

    return ret

@tool(args_schema=NameSearchInput)
def search_name(name: str):
    """
    Finds cards based on a search string.
    If the search string is contained in some card names, those are preferred.
    Otherwise, returns the 5 most relevant cards based on Levenshtein distance.
    Use this to disambiguate cards from the user's query, NOT to search for cards
    you know from your training data.
    """
    ratios = []
    contained_in = []
    name = name.lower()
    
    for card in data.DB:
        card_name = card["name"]
        if name in card_name.lower():
            contained_in.append(card["name"])
        ratios.append([card_name, Levenshtein.ratio(name, card_name)])  
    
    if len(contained_in) > 0:
        return contained_in

    return [x[0] for x in sorted(ratios, key=lambda x: x[1], reverse=True)[:5]]

def evaluate_filter(card, fltr, eval_tag_children=True):
    if type(fltr) == bool: #reduce initialization edge case
        return fltr
    if type(fltr) == AndFilter:
        return reduce(lambda x,y: evaluate_filter(card, x, eval_tag_children) and evaluate_filter(card, y, eval_tag_children), fltr.value, True)
    if type(fltr) == OrFilter:
        return reduce(lambda x,y: evaluate_filter(card, x, eval_tag_children) or evaluate_filter(card, y, eval_tag_children), fltr.value, False)
    
    if type(fltr) == TagFilter and eval_tag_children:
        tag = fltr.value
        tags = get_tag_descendants(tag) + [tag]
        tag_filters = [TagFilter(value=t) for t in tags]
        return evaluate_filter(card, OrFilter(value=tag_filters), False)

    op_dict = COLOR_OP_DICT if type(fltr) == ColorFilter else OP_DICT
    field = fltr.field if type(fltr) == ArithmeticFilter else fltr.kind
    # Card may not contain the field we're searching for
    # E.g not all cards contain the power and toughness fields
    card_val = card.get(field) 
    if card_val is None:
        return False
    return op_dict[fltr.op](card_val, fltr.value)

@tool(args_schema=QueryInput)
def query_json(filters, limit=15):
    """
    Execute a query on the JSON Lines card database.

    IMPORTANT:
    - This tool supports complex boolean expressions.
    - Always send the complete query tree in a single call.
    - Do NOT split AND/OR expressions into multiple calls.
    - For example, blue cards with tag A or B must be searched with
    AndFilter([
        ColorFilter(value=["U"], op="="),
        OrFilter([TagFilter(value=A), TagFilter(value=B)])
    ])
    and sent as one query.
    - This tool is stateless. Do NOT call it with the same filters;
    the returned results will be identical to the previous ones.
    """
    ret = []

    for card in data.DB:
        if evaluate_filter(card, filters):
            ret.append(card)

    ret = sorted(ret, key=itemgetter("edhrec_rank"))

    return ret[:limit]


@tool(args_schema=LinkFetchInput)
def get_links(card_names):
    """
    Receives a list of card names and returns a list of links to each card's page on scryfall.
    Order is preserved.
    """
    return [data.CARD_LINKS.get(name) for name in card_names]

if __name__ == "__main__":
    load_data()

    q = QueryInput(filters=AndFilter(value=[
        ColorFilter(op="=", value=["W"]),
        TagFilter(value="protection")
    ]))

    from pprint import pprint
    
    print("Protection descendants:")
    pprint(get_tag_descendants("protection"))

    pprint(query_json.invoke(q.model_dump()))

    #pprint(get_tag_children.invoke({"tag": "protection"}))
    #pprint(get_tag_descendants("burn"))
