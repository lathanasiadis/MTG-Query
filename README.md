# MTG Query

A tool that helps you find *Magic: The Gathering* cards using natural language queries.

It relies on a locally downloaded copy of [scryfall](https://scryfall.com/) card data, [scryfall tagger](https://tagger.scryfall.com) oracle tags
and a LangChain agent that searches them in response to the user's prompt.

## Features

You can ask MTG Query to find cards based on:

- color

- mana value

- price

- rarity

- type

- effect type (e.g card draw, removal). When doing this, the agent will find the relevant oracle tags and search for cards that match them.

- synergy with other cards. When doing this, the agent will find cards with the same or similar tags as that card.

The agent has memory, i.e remembers your past messages and its responses.
This is useful when the user mentions an ambigous card name.
For example, if you ask for cards that synergize well with Alesha, the agent will ask if you mean *Alesha, Who Smiles at Death* or *Alesha, Who Laughs at Fate*.
After your response, the agent will answer your original question.

Cards mentioned in the agent's response are linked to their page on scryfall.

Check **Usage** for an overview of the MTG Query TUI.

## Installation

MTG Query uses a LangChain agent that requires a DeepSeek API key.

Rename `example.env` to `.env` and fill it in.

Additionally, you can set up LangSmith tracing if you're curious on what the agent
is doing behind the scenes by following the instructions in `example.env`.
(This is optional.)

Dependencies are manages with `uv`. After installing `uv`, run

`uv sync`

to download the dependencies and create the virtual environment. Then, run

`uv run mtgquery.py`

to run the actual app.

## Usage

Besides prompting, MTG Query offers a simple TUI via a small set of commands.
All you have to do is use them in place of a prompt; they will be detected and handled accordingly.

- `new`

Wipe the agent's memory, meaning that it will no longer remember your previews messages and its replies.
Useful before asking an unrelated question, so that a) its context window stays small and b) it uses less tokens.

- `save`

Save the current conversation (including prompts) in `conversation.md`.
If it exists, it will be saved in `conversation2.md` (and so on, if that file exists too).

- `exit`

Gracefully exit the application.

- `help`

Print this help message.


