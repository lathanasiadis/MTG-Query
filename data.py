from dataclasses import dataclass
from typing import Optional
import chromadb
from chromadb.api import ClientAPI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from TagTree import TagTree
from constants import Constants as C
from utils import load_json_file
from card import Card, load_cards, create_automaton


@dataclass
class _State:
    # Global objects that need to be accessed by the agent's tools, lazily initialized
    _cards: Optional[list[Card]] = None
    _tags = None
    _tag_tree = None
    _card_links = None
    _emb_model: Optional[HuggingFaceEmbeddings] = None
    _chroma_client: Optional[ClientAPI] = None
    _qa_store: Optional[Chroma] = None
    _rules_store: Optional[Chroma] = None
    _automaton = None

    # Cards
    @property
    def cards(self):
        if self._cards is None:
            self._cards = load_cards()
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

    # Vector Stores
    @property
    def rules_store(self):
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=C.CHROMA_DB)
        if self._emb_model is None:
            self._emb_model = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5",
                encode_kwargs={"batch_size": 64, "normalize_embeddings": True},
            )
        if self._rules_store is None:
            self._rules_store = Chroma(
                client=self._chroma_client,
                collection_name=C.CHROMA_COLLECTIONS["RULES"],
                embedding_function=self._emb_model
            )
        return self._rules_store

    @rules_store.setter
    def rules_store(self, rules_store):
        self._rules_store = rules_store

    @property
    def qa_store(self):
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=C.CHROMA_DB)
        if self._emb_model is None:
            self._emb_model = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5",
                encode_kwargs={"batch_size": 64, "normalize_embeddings": True},
            )
        if self._qa_store is None:
            self._qa_store = Chroma(
                client=self._chroma_client,
                collection_name=C.CHROMA_COLLECTIONS["STACKEX"],
                embedding_function=self._emb_model
            )
        return self._qa_store

    @qa_store.setter
    def qa_store(self, qa_store):
        self._qa_store = qa_store

    @property
    def automaton(self):
        if self._automaton is None:
            self._automaton = create_automaton()
        return self._automaton

    @automaton.setter
    def automaton(self, automaton):
        self._automaton = automaton

State = _State()

def load_tool_dependencies():
    """
    Simple workaround to force the lazy evaluation,
    so that the agent doesn't try to do it in parallel.
    """
    _ = State.cards
    _ = State.automaton
    # vector stores will also load chroma db and emb model
    _ = State.rules_store
    _ = State.qa_store