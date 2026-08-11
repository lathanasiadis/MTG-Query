from dataclasses import dataclass

from TagTree import TagTree
from constants import Constants as C
from utils import load_json_file

@dataclass
class _State:
    # Global objects that need to be accessed by the agent's tools, lazily initialized
    _cards = None
    _tags = None
    _tag_tree = None
    _card_links = None
    _emb_model = None

    # Cards
    @property
    def cards(self):
        if self._cards is None:
            self._cards = load_json_file(C.FILES["CARDS"])
        return self._cards

    @cards.setter
    def cards(self, cards):
        self._cards = cards

    # Tag Tree
    @property
    def tag_tree(self):
        if self._tag_tree is None:
            self._tag_tree = TagTree(C.ORACLE["TAGS"])
        return self._tag_tree

    @tag_tree.setter
    def tag_tree(self, tag_tree):
        self._tag_tree = tag_tree

    
State = _State()
