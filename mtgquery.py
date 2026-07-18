import json
import time
import os
from enum import Enum

from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain.messages import HumanMessage
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver 
from langchain.tools import tool
from rich.console import Console
from rich.markdown import Markdown

from constants import Constants as C
from fetch_data import fetch_data, load_data
from tools import search_name, get_tags, get_typal_tags, get_tutor_tags, query_json, get_links
import data


def conv_filename():
    conv_files = list(filter(lambda x: "conversation" in x, os.listdir(".")))
    # No previous conversation file found
    if len(conv_files) == 0:
        return "conversation.md"
    return f"conversation{len(conv_files) + 1}.md"

def print_help():
    print("Besides prompting, you can use these commands:\n")
    print("- save")
    print("Saves the current conversation to conversation.md, for later viewing.\n")
    print("- new")
    print("Wipes the agent's memory. Useful when you want to ask an unrelated question afterwards.\n")
    print("- exit")
    print("Exits the application gracefully.\n")
    print("- help")
    print("Display this message.\n")

if __name__ == "__main__":
    load_dotenv()
    fetch_data()
    load_data()

    search_agent = create_agent(
        model="deepseek-chat",
        tools=[search_name, get_tags, get_typal_tags, get_tutor_tags, query_json],
        system_prompt="""
        You are a Magic: the Gathering card query system. You retrieve cards based on the user's input.
        
        Do NOT try to guess tag names! Use the get_tags tool!

        If a user mentions an ambiguous card name, you should ask for clarification by presenting the possible card names.

        Do NOT use search_name with cards you know from your training data! Only use it to search for cards the user mentions.

        If any tool gets call limited, don't try calling it again during the same run.
        """,
        middleware = [
            ToolCallLimitMiddleware(tool_name="query_json", run_limit=5),
            ToolCallLimitMiddleware(tool_name="search_name", run_limit=5)
        ],
        checkpointer=InMemorySaver()
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

    config = {"configurable": {"thread_id": str(int(time.time()))}}
    
    current_convo = ""
    while True:
        prompt = input("\n>>> Prompt: ")

        prompt_lower = prompt.lower()
        if prompt_lower == "save":
            if current_convo == "":
                print("Current conversation is empty!")
            else:
                filename = conv_filename()
                with open(filename, "w") as f:
                    f.write(current_convo)
                print(f"Conversation saved to {filename}!")
        elif prompt_lower == "new":
            search_agent.invoke(
                {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]},
                config
            )
            current_convo = ""
            print("Message history cleared!")
        elif prompt_lower == "help":
            print_help()
        elif prompt_lower == "exit":
            break
        else:
            search_question = HumanMessage(content=prompt)
            search_response = search_agent.invoke(
                {"messages": [search_question]},
                config
            )
            link_question = HumanMessage(content=search_response["messages"][-1].content)
            link_response = link_agent.invoke(
                {"messages": [link_question]}
            )

            last_response = link_response["messages"][-1].content
            current_convo += f"> {prompt}\n\n{last_response}\n"

            console = Console()
            markdown = Markdown(last_response)
            console.print(markdown)


