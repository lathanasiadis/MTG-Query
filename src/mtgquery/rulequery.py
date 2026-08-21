import datetime as dt
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek

from mtgquery.constants import prompts
from mtgquery.state import State, load_tool_dependencies
from mtgquery.TokenUsage import TokenUsage
from mtgquery.tools import find_card, retrieve


@dataclass
class Queries:
    """
    natural language queries aimed to retrieve relevant info.
    rule_queries: aimed at the comprehensive MTG rulebook. Return at most 5.
    qa_queries: aimed at verified Q&As. Return at most 5.
    """
    rule_queries: list[str]
    qa_queries: list[str]

if __name__ == "__main__":
    load_dotenv()
    load_tool_dependencies()
    token_usage = TokenUsage()

    model = ChatDeepSeek(model="deepseek-chat")

    queries_agent = create_agent(
        model="deepseek-chat",
        system_prompt=prompts.RETRIEVAL,
        response_format=Queries
    )

    answer_agent = create_agent(
        model="deepseek-v4-flash",
        system_prompt=prompts.ANSWER,
    )

    prompt = "Question:\n" + input(">>> Enter your rules question: ") + "\n"

    # Add detected card info to prompt
    cards_detected = State.automaton.detect(prompt)
    if len(cards_detected) != 0:
        unique_cards = [card for card in cards_detected if type(card) == str]
        multiple_cards = [card for card in cards_detected if type(card) == list]
        for cards in multiple_cards:
            print("Multiple results detected for a given card. Which one of these is right? Reply with the line number.")
            for i, card in enumerate(cards):
                print(f"{i+1}. {card}")
            while True:
                num = input(">>> ")
                if num.isnumeric():
                    num = int(num)
                    if num > 0 and num <= len(cards):
                        unique_cards.append(cards[num-1])
                        break
                print("Wrong line number detected!")

        cards = [find_card(c) for c in unique_cards]
        cards = [str(c.for_rules_prompt()) for c in cards if c is not None]

        prompt += f"\nRelated Cards:\n{"\n".join(cards)}"

    query_response = queries_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )

    token_usage.add(query_response["messages"][-2].usage_metadata)

    structured_response = query_response["structured_response"]

    retrieved_documents = set()
    for rule_query in structured_response.rule_queries:
        retrieved_documents.update(retrieve(rule_query, "rules"))
    for qa_query in structured_response.qa_queries:
        retrieved_documents.update(retrieve(qa_query, "qa"))

    selected_titles = []
    selected = ""

    for r in retrieved_documents:
        with open(r, "r") as f:
            text = "Document " + r + " :\n" + f.read() + "\n"
        response = model.invoke([
            ("system", prompts.SELECTION),
            ("human", f"{prompt}\n\n{text}")
        ])
        token_usage.add(response.usage_metadata)
        classification = str(response.content).lower()
        if classification == "yes":
            selected_titles.append(r)
            selected += text
        elif classification != "no":
            print("[WARNING] wrong selection model output detected!")


    answer = answer_agent.invoke(
        {"messages": [{"role": "user", "content": f"{prompt}\n{selected}"}]}
    )

    print(answer["messages"][-1].content)

    print("\nSources used:\n")
    for doc in selected_titles:
        print(f"- {doc}")

    print()
    token_usage.add(answer["messages"][-1].usage_metadata)
    token_usage.calculate()
