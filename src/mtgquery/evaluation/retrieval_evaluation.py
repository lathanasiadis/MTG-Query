import argparse
import json
import re
from collections.abc import Callable
from pathlib import Path
from time import sleep

import pandas as pd
import requests

from mtgquery.constants import files, links
from mtgquery.state import State
from mtgquery.tools import find_card, retrieve


def create_dataset():
    dataframes: list[pd.DataFrame] = []

    for level in ["0", "1", "2", "3", "Corner Case"]:
        params = {
            "count": 15,
            "level": [level],
            "complexity": ["Simple", "Intermediate", "Complicated"],
            "legality": "all",
            "from": "MTG-Query"
        }

        # Respect rate limit
        if level != "0":
            sleep(2)
        r = requests.get(
            links.RULESGURU_API,
            params = {
                "json": json.dumps(params)
            }
        )
        content = json.loads(r.content.decode())

        df = pd.DataFrame({
            "id": [x["id"] for x in content],
            "level": [x["level"] for x in content],
            "complexity": [x["complexity"] for x in content],
            "tags": [",".join(x["tags"]) for x in content],
            "question": [x["questionSimple"] for x in content],
            "answer": [x["answerSimple"] for x in content],
            "rules": [",".join(x["citedRules"].keys()) for x in content]
        })
        dataframes.append(df)

    # This leads to multiple lines per index, but we don't care since
    # we only want to export as csv
    dataset = pd.concat(dataframes)
    dataset.to_csv(files.RETRIEVAL_DATASET, index=False)


def get_rule_stem(rule: str) -> str:
    """
    For a given subrule, e.g 608.3a, return the rule it belongs to (608)
    If the general rule is 701 or 702 (keyword abilities or actions),
    return the subrule as well, but without the letter(s) specifying specific
    sentences
    """
    return re.sub("[a-zA-Z ]", "", rule) if "701" in rule or "702" in rule \
        else re.sub("[a-zA-Z ]", "", rule).split(".")[0]


def _question_only(question: str, k: int = 5):
    results = retrieve(question, corpus="rules", k=k)
    retrieved_rules = {get_rule_stem(result.id) for result in results}
    return retrieved_rules


def _append_cards(question: str, k: int = 5):
    detected_cards = State.automaton.detect(question)
    if len(detected_cards) > 0:
        detected_cards = [find_card(c) for c in detected_cards]
        question += "\n".join(str(detected_cards))

    return _question_only(question, k)


def eval(
    solution_func: Callable[[str, int], set[str]],
    results_path: Path,
    k: int =5
):
    dataset = pd.read_csv(files.RETRIEVAL_DATASET).dropna().reset_index()
    results = []
    for _, row in dataset.iterrows():
        question = row["question"]
        cited_rules = {get_rule_stem(rule) for rule in row["rules"].split(",")}
        retrieved_rules = solution_func(question, k)
        results.append([
            row["id"],
            ",".join(cited_rules),
            ",".join(retrieved_rules)
        ])
    results_df = pd.DataFrame(results, columns=["id", "cited_rules", "retrieved_rules"])
    results_df.to_csv(results_path, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["fetch", "eval"],
        default="eval"
    )
    args = parser.parse_args()

    if args.mode == "fetch":
        create_dataset()
    else:
        Path.mkdir(files.RESULTS_DIR, exist_ok=True)
        eval(_question_only, files.RESULTS_DIR.joinpath("retrieval_question_only.csv"))
        eval(_append_cards, files.RESULTS_DIR.joinpath("retrieval_append_cards.csv"))


if __name__ == "__main__":
    main()
