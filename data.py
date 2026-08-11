from dataclasses import dataclass
from langchain_huggingface import HuggingFaceEmbeddings
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

    # Embedding Model
    @property
    def emb_model(self):
        if self._emb_model is None:
            self._emb_model = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5",
                encode_kwargs={"batch_size": 64, "normalize_embeddings": True},
            )
        return self._emb_model

    @emb_model.setter
    def emb_model(self, emb_model):
        self._emb_model = emb_model

    
State = _State()
