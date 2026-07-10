from operator import itemgetter
from typing import Union, Literal, List
from pydantic import BaseModel, Field
from langchain.tools import tool
import data

class ArithmeticFilter(BaseModel):
    field: Literal["cmc", "price"]
    op: Literal["<", "<=", "=", ">=", ">"]
    value: int | float = Field(
            description = "Use int when comparing cmc and float when comparing prices. Prices are stored in EUR."
    )

class ColorFilter(BaseModel):
    field: Literal["color_identity"]
    op: Literal["<=", "=", ">="]
    value: List[Literal["W", "U", "B", "R", "G"]]

class RarityFilter(BaseModel):
    field: Literal["rarity"]
    op: Literal["="]
    value: Literal["common", "uncommon", "rare", "mythic"]

class TagFilter(BaseModel):
    field: Literal["oracle_tags"]
    op: Literal["contains"]
    value: List[str]

class TypeFilter(BaseModel):
    field: Literal["type_line"]
    op: Literal["in"]
    value: str = Field(
        description="Value that is contained in the card's type line. Should be lowercase only."
    )

class NameFilter(BaseModel):
    field: Literal["name"]
    op: Literal["="]
    value: str

Filter = Union[
    ArithmeticFilter,
    ColorFilter,
    RarityFilter,
    TagFilter,
    TypeFilter,
    NameFilter
]
    
class QueryInput(BaseModel):
    filters: list[Filter]

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
    "in": lambda x,y: y in x
}

COLOR_OP_DICT = {
    "<=": lambda x,y: set(y).issubset(set(x)),
    "=": lambda x,y: set(x) == set(y),
    ">=": lambda x,y: set(y).issuperset(set(x))
}

@tool(args_schema=QueryInput)
def query_json(filters, limit=10):
    """
    Find an MTG card based on a set of filters.

    This tool is NOT paginated; calling it with the same filters
    will return the same results.
    """
    ret = []
    for card in data.DB:
        all_filters_passed = True
        
        for fltr in filters:
            card_val = card.get(fltr.field)
            if card_val is None:
                all_filters_passed = False
                break

            op_dict = COLOR_OP_DICT if type(fltr) == ColorFilter else OP_DICT
            
            if not op_dict[fltr.op](card_val, fltr.value):
                all_filters_passed = False
                break
        
        if all_filters_passed:
            ret.append(card)

    ret = sorted(ret, key=itemgetter("edhrec_rank"))

    return ret[:limit]

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

@tool(args_schema=LinkFetchInput)
def get_links(card_names):
    """
    Receives a list of card names and returns a list of links to each card's page on scryfall.
    Order is preserved.
    """
    return [data.CARD_LINKS.get(name) for name in card_names]

