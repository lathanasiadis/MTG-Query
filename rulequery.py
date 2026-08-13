from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from tools import search_rules, search_qa, find_card
from data import State, load_tool_dependencies
from constants import Prompts


if __name__ == "__main__":
    load_dotenv()
    load_tool_dependencies()

    model = ChatDeepSeek(model="deepseek-v4-flash")

    agent = create_agent(
        model=model,
        tools=[search_rules, search_qa],
        system_prompt=Prompts.retrieval
    )

    prompt = "Question:\n" + input(">>> Enter your rules question: ") + "\n"

    found = set()
    for end_idx, (key_len, orig) in State.automaton.iter(prompt.lower()):
        start_idx = end_idx - key_len + 1
        start_ok = start_idx == 0 or not prompt[start_idx-1].isalnum()
        end_ok = end_idx == len(prompt) - 1 or not prompt[end_idx+1].isalnum()
        if start_ok and end_ok:
            found.add(orig)

    if len(found) != 0:
        prompt += f"\nRelated Cards:\n{"\n".join([str(find_card(c)) for c in found])}"

    response = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )

    sources = response["messages"][-1].content.split("\n")

    rel_docs = ""
    for doc in sources:
        with open(doc[8:], "r") as f:
            rel_docs += f.read() + "\n"

    for chunk in model.stream(Prompts.rules.format(question=prompt, rel_docs=rel_docs)):
        print(chunk.text, end="", flush=True)

    print("\nSources used:\n")
    for doc in sources:
        print(f"- {doc}")
        