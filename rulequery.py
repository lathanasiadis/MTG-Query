from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from tools import find_card, retrieve
from data import State, load_tool_dependencies
from constants import Prompts

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

    model = ChatDeepSeek(model="deepseek-chat")

    queries_agent = create_agent(
        model="deepseek-chat",
        system_prompt=Prompts.retrieval,
        response_format=Queries
    )

    answer_agent = create_agent(
        model="deepseek-v4-flash",
        system_prompt=Prompts.rules,
    )

    prompt = "Question:\n" + input(">>> Enter your rules question: ") + "\n"

    # Add detected card info to prompt
    cards_detected = State.automaton.detect(prompt)
    if len(cards_detected) != 0:
        # TODO: handle card disambiguation
        cards = [find_card(c) for c in cards_detected]
        cards = list(filter(lambda x: x is not None, cards))
        cards = [str(c.for_rules_prompt()) for c in cards]

        prompt += f"\nRelated Cards:\n{"\n".join(cards)}"

    response = queries_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )

    structured_response = response["structured_response"]

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
            ("system", Prompts.selection),
            ("human", f"{prompt}\n\n{text}")
        ])
        response = str(response.content).lower()
        if response == "yes":
            selected_titles.append(r)
            selected += text
        elif response != "no":
            print("[WARNING] wrong selection model output detected!")

        
    answer = answer_agent.invoke(
        {"messages": [{"role": "user", "content": f"{prompt}\n{selected}"}]}
    )

    print(answer["messages"][-1].content)

    # for chunk in answer_model.stream(Prompts.rules.format(question=prompt, rel_docs=selected)):
    #     print(chunk.text, end="", flush=True)

    print("\nSources used:\n")
    for doc in selected_titles:
        print(f"- {doc}")
