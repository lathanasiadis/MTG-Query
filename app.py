import streamlit as st
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek

from constants import Prompts
from rulequery import Queries
from TokenUsage import TokenUsage
from tools import find_card, retrieve

if "stage" not in st.session_state:
    from data import State, load_tool_dependencies
    load_dotenv()
    load_tool_dependencies()

    st.session_state.stage = "initialized"
    st.session_state.app = State
    st.session_state.queries_agent = create_agent(
        "deepseek-chat",
        system_prompt = Prompts.retrieval,
        response_format = Queries
    )
    st.session_state.answer_agent = create_agent(
        "deepseek-v4-flash",
        system_prompt = Prompts.rules
    )
    st.session_state.clf_model = ChatDeepSeek(model="deepseek-chat")
    st.session_state.token_usage = TokenUsage()


queries_agent = st.session_state.queries_agent
answer_agent = st.session_state.answer_agent
clf_model = st.session_state.clf_model
token_usage = st.session_state.token_usage

with st.form("question_forum"):
    prompt = st.text_area("Enter your rules question: ")
    submitted = st.form_submit_button("Submit")
    status = st.empty()

if submitted:
    cards_detected = st.session_state.app.automaton.detect(prompt)
    if len(cards_detected) > 0:
        cards = [find_card(c) for c in cards_detected]
        card_names = [c.name for c in cards if c is not None]
        cards = [str(c.for_rules_prompt()) for c in cards if c is not None]
        prompt += f"\nRelated Cards:\n{"\n".join(cards)}"
        with st.sidebar:
            st.write("# Mentioned cards")
            for card in card_names:
                st.write(f"- {card}")

    status.caption("Generating retrieval queries…")
    query_response = queries_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )
    structured_response = query_response["structured_response"]
    token_usage.add(query_response["messages"][-2].usage_metadata)

    retrieved_documents = set()
    for rule_query in structured_response.rule_queries:
        retrieved_documents.update(retrieve(rule_query, "rules"))
    for qa_query in structured_response.qa_queries:
        retrieved_documents.update(retrieve(qa_query, "qa"))

    status.caption("Picking relevant results…")
    selected_titles = []
    selected = ""
    for r in retrieved_documents:
        with open(r, "r") as f:
            text = "Document " + r + " :\n" + f.read() + "\n"
        response = clf_model.invoke([
            ("system", Prompts.selection),
            ("human", f"{prompt}\n\n{text}")
        ])
        token_usage.add(response.usage_metadata)
        classification = str(response.content).lower()
        if classification == "yes":
            selected_titles.append(r)
            selected += text
        elif classification != "no":
            status.caption("Warning: selection model returned an unexpected result.")

    status.caption("Generating result…")
    answer = answer_agent.invoke(
        {"messages": [{"role": "user", "content": f"{prompt}\n{selected}"}]}
    )
    token_usage.add(answer["messages"][-1].usage_metadata)
    status.empty()
    st.write(answer["messages"][-1].content)
    with st.sidebar:
        st.write("# Token costs")
        costs = token_usage.costs()
        st.write(f"- Input (cache hit) : {costs[0]:.4f}")
        st.write(f"- Input (cache miss): {costs[1]:.4f}")
        st.write(f"- Output            : {costs[2]:.4f}")
