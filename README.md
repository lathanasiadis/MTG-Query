# MTG Query

AI tools that helps you with *Magic: The Gathering*.
Currently consisting of `rulequery.py`, a RAG application that answers rule questions.

## Features

- **Card detection:** You can mention card names in your query.
The full info (oracle text, mana cost, etc) of every detected card will be appended to your prompt.

- **Split cards:** No need to mention their full name (X // Y). Just X or Y suffices.
Works for every card type with two separate cards on it (adventures, omens, prepared spells, etc)

- **Legendary cards:** You can skip their epithet if it is not needed for disambiguation.
For example, you can refer to *Isshin, Two Heavens as One* as *Isshin*.

- **Cited sources:** Before answering your question, a retrieval system finds the most relevant rules and Q&As from stack exchange.
These are fed to the model as sources, so you can inspect them to validate the model's answer.


## Installation

MTG Query uses `langchain`'s DeepSeek integration.
 
You need to rename `example.env` to `.env` and fill in your API key.

Additionally, you can set up LangSmith tracing if you're curious on what the agent
is doing behind the scenes by following the instructions in `example.env`.
(This is optional.)

Dependencies are managed with `uv`. After installing it, run

`uv sync`

to download the dependencies and create the virtual environment. Then, run

`uv run rulequery.py`

to run the actual app.

## Example

```
>>> Enter your rules question: Avery controls a tapped Skyshroud Elf and Ashnod's Altar. Can they cast Ragost, Deft Gastronaut?
No.

Skyshroud Elf’s tapped status only prevents its `{T}: Add {G}` ability. It still has `{1}: Add {R} or {W}`, which does not require tapping. However, activating that ability costs `{1}`, and Avery has no mana to pay for it.

Ashnod’s Altar could produce `{C}{C}`, but only by sacrificing a creature. The only creature Avery controls is Skyshroud Elf itself. If Avery sacrifices it to the Altar, Skyshroud Elf leaves the battlefield, so its `{1}` filter ability can no longer be used to turn that colorless mana into red or white.

So there is no sequence that produces both `{R}` and `{W}`. Ashnod’s Altar’s colorless mana alone cannot pay Ragost’s colored mana cost. Therefore, Avery cannot cast Ragost, Deft Gastronaut.

Sources used:

- downloaded_data/rules/6. Spells, Abilities, and Effects/602. Activating Activated Abilities.txt
- downloaded_data/stackex/boardgames.stackexchange_0000030058.txt
- downloaded_data/stackex/boardgames.stackexchange_0000020983.txt
- downloaded_data/stackex/boardgames.stackexchange_0000054718.txt
- downloaded_data/stackex/boardgames.stackexchange_0000015340.txt
```
