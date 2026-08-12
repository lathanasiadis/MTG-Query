from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from tools import search_rules, search_qa, find_card
from data import load_vector_stores
from constants import Prompts


if __name__ == "__main__":
    load_dotenv()
    load_vector_stores()

    model = ChatDeepSeek(model="deepseek-v4-flash")

    agent = create_agent(
        model=model,
        tools=[search_rules, search_qa, find_card],
        system_prompt=Prompts.retrieval
    )

    prompt = input(">>> Enter your rules question: ")

    response = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )

    sources = response["messages"][-1].content.split("\n")
    card_sources = list(filter(lambda x: x.startswith("card: "), sources))
    doc_sources = list(filter(lambda x: x.startswith("source: "), sources))

    if len(card_sources) + len(doc_sources) != len(sources):
        print("[WARNING] The LLM failed to prefix some sources.")
        print(sources)

    rel_cards = "\n".join([str(find_card.invoke({"name": card[6:]})) for card in card_sources])

    rel_docs = ""
    for doc in doc_sources:
        with open(doc[8:], "r") as f:
            rel_docs += f.read() + "\n"

    for chunk in model.stream(Prompts.rules.format(q=prompt, rel_cards=rel_cards, rel_docs=rel_docs)):
        print(chunk.text, end="", flush=True)

    print("\nSources used:\n")
    for doc in doc_sources:
        print(f"- {doc}")
        