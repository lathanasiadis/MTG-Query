import json
from enum import Enum

from dotenv import load_dotenv
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
from tools import search_name, get_tags, get_typal_tags, get_tutor_tags, query_json, get_links
import data

def load_json_file(filename):
    with open(filename, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    load_dotenv()
    fetch_data()

    data.DB = load_json_file(C.FILES["CARDS"])
    # Right now, using the tag names without their descriptions.
    # They seem to not be essential, and this way the agent requires less tokens.
    data.TAGS = load_json_file(C.FILES["TAGS"]).keys()
    data.TAGS_TUTOR = load_json_file(C.FILES["TAGS_TUTOR"]).keys()
    data.TAGS_TYPAL = load_json_file(C.FILES["TAGS_TYPAL"]).keys()

    data.CARD_LINKS = load_json_file(C.FILES["LINKS"])

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

    prompt = input(">>> Prompt: ")

    search_question = HumanMessage(content=prompt)
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


