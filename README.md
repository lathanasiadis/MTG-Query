# MTG Query

A tool that helps you find *Magic: The Gathering* cards using natural language queries.

It relies on a locally downloaded copy of [scryfall](https://scryfall.com/) card data, [scryfall tagger](https://tagger.scryfall.com) oracle tags
and a LangChain agent that searches them in response to the user's prompt.
The copy is updated when the progrma is launched, if it is older than 24 hours.

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

You need to rename `example.env` to `.env` and fill it in.

Additionally, you can set up LangSmith tracing if you're curious on what the agent
is doing behind the scenes by following the instructions in `example.env`.
(This is optional.)

Dependencies are managed with `uv`. After installing it, run

`uv sync`

to download the dependencies and create the virtual environment. Then, run

`uv run mtgquery.py`

to run the actual app.

## Usage

Besides prompting, MTG Query offers a simple TUI via a small set of commands.
All you have to do is use them in place of a prompt; they will be detected and handled accordingly.

- `new`

Wipe the agent's memory, meaning that it will no longer remember your previews messages and its replies.
Useful before asking an unrelated question, so that a) its context window stays small (agent is less prone to mistakes) and b) it uses less tokens.

- `save`

Save the current conversation (including prompts) in `conversation.md`.
User's prompts are inserted as markdown quotes.
If it exists, it will be saved in `conversation2.md` (and so on, if that file exists too).

- `exit`

Gracefully exit the application.

- `help`

Print this help message.

## Example Runs

Some example runs can be found in [examples/](examples/). They were produced with the `save` TUI command.

- [simple search](examples/01-simple-attribute-filters.md): A query that is satisfied with attribute filters only. (in this example: color, card type, rarity, mana cost and price)

- [effect search](examples/02-gameplay-effect.md): Searching for a broad gameplay term ("protection") combined with an attribute filter. Behind the scenes, the agent reasons which of the 2000+ available oracle tags match the user's question and returns cards that contain them.

- [synergy search](examples/03-synergy.md): The user asks for cards that synergize with another card. Behind the scenes, the agent finds cards that have the same or similar tags as the mentioned card.

- [agent asking for clarification](examples/04-clarification.md): The user wants to find synergies for a card, but there are multiple matches for the name he mentioned. The agent presents the possible options before completing the original request.

- [user asking a follow up question](examples/05-follow-up-question.md): The user can also ask follow up questions! In this example, after asking for cards that synergize well with another, the user asks the agent to limit its search to two types of cards.

