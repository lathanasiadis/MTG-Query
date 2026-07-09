from dotenv import load_dotenv

import json
from enum import Enum
from operator import itemgetter
from typing import Union, Literal, List

import Levenshtein
from pydantic import BaseModel, Field
from langchain_openrouter import ChatOpenRouter
from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain.messages import HumanMessage
from langchain.tools import tool

from rich.console import Console
from rich.markdown import Markdown

from constants import Constants as C
from fetch_data import fetch_data

def load_json_file(filename):
    with open(filename, "r") as f:
        return json.load(f)

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
    op: Literal["contains", "has-one-of"]
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
    "in": lambda x,y: y in x,
    "has-one-of": has_one_of_op
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
    for card in DB:
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
    return TAGS

@tool
def get_typal_tags():
    """
    Returns a list containing every oracle tag referencing typals.
    Use this ONLY to find tags for typal/tribal/kindred synergies (i.e synergies with specific creature types)
    or for their hate versions (i.e negative effects to specific creature types).
    """
    return TAGS_TYPAL

@tool
def get_tutor_tags():
    """
    Returns a list containing every oracle tag referencing tutors (i.e cards that search for other cards).
    Use this ONLY to find tags for searching for specific cards.
    """
    return TAGS_TUTOR

@tool(args_schema=TagSearchInput)
def search_tags(keywords):
    """
    Returns the tag names that contain a set of keywords.
    Tag descriptions are also searched, for tags that contain one.
    """
    ret = set()

    for k,v in TAGS.items():
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
    
    for card in DB:
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
    return [CARD_LINKS.get(name) for name in card_names]

if __name__ == "__main__":
    load_dotenv()
    fetch_data()

    DB = load_json_file(C.FILES["CARDS"])
    # Right now, using the tag names without their descriptions.
    # They seem to not be essential, and this way the agent requires less tokens.
    TAGS = load_json_file(C.FILES["TAGS"]).keys()
    TAGS_TUTOR = load_json_file(C.FILES["TAGS_TUTOR"]).keys()
    TAGS_TYPAL = load_json_file(C.FILES["TAGS_TYPAL"]).keys()

    CARD_LINKS = load_json_file(C.FILES["LINKS"])

    search_agent = create_agent(
        model="deepseek-chat",
        tools=[search_name, get_tags, get_typal_tags, get_tutor_tags, query_json],
        system_prompt="""
        You are a Magic: the Gathering card query system. You retrieve cards based on the user's input.
        
        Do NOT try to guess tag names! Use the get_tags tool!

        Do NOT use search_name with cards you know from your training data! Only use it to search for cards the user mentions.

        If any tool gets call limited, don't try calling it again during the same run.
        """,
        middleware = [
            ToolCallLimitMiddleware(tool_name="query_json", run_limit=5),
            ToolCallLimitMiddleware(tool_name="search_name", run_limit=5)
        ]
    )

    link_agent = create_agent(
        model="deepseek-chat",
        tools=[get_links],
        system_prompt="""
        You are a Magic: the Gathering link injector.
        You will receive a markdown text describing MtG cards and you will edit it so that each card is linked to its scryfall page.
        Use the get_links tool.
        Do not alter the text in any other way!
        If the input does not contain any card names (e.g an error message), return it as-is.
        """,
        middleware = [
            ToolCallLimitMiddleware(tool_name="get_links", run_limit=3)
        ]
    )

    search_question = HumanMessage(content="I'm looking for white mythic cards that cost less than 3$")
    search_response = search_agent.invoke(
        {"messages": [search_question]}
    )
    link_question = HumanMessage(content=search_response["messages"][-1].content)
    link_response = link_agent.invoke(
        {"messages": [link_question]}
    )

    console = Console()
    markdown = Markdown(link_response["messages"][-1].content)
    console.print(markdown)


