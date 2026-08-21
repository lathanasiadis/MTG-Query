from pathlib import Path

_constants_dir = Path(__file__).parent.resolve()
_app_dir = _constants_dir.parent.resolve().parent.resolve().parent.resolve()

DATA_DIR_NAME = "data"
DATA_DIR = _app_dir.joinpath(DATA_DIR_NAME)

ORACLE_CARDS_ALL = DATA_DIR.joinpath("oracle-cards-all.json")
ORACLE_CARDS = DATA_DIR.joinpath("oracle-cards.json")
ORACLE_TAGS = DATA_DIR.joinpath("oracle-tags.json")

CARDS = DATA_DIR.joinpath("cards.json")
LINKS = DATA_DIR.joinpath("card-links.json")
TIMESTAMP = DATA_DIR.joinpath(".timestamp")

# convert to str because Chroma expects str | None
CHROMA_DB = str(_app_dir.joinpath(".chroma_db"))

COMP_RULES = DATA_DIR.joinpath("magic_cr.txt")
RULES_DIR = DATA_DIR.joinpath("rules")
STACKEX_DIR = DATA_DIR.joinpath("stackex")

REMOVED_TAGS = DATA_DIR.joinpath(".removed-tags.txt")
TAG_LLM_DESCS = DATA_DIR.joinpath("llm-descriptions.json")
