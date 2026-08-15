from dataclasses import dataclass
from functools import cached_property
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from TagTree import TagTree
from constants import Constants as C
from card import Card, load_cards
from automaton import Automaton

@dataclass
class _State:
    @cached_property
    def cards(self) -> list[Card]:
        return load_cards()

    @cached_property
    def automaton(self) -> Automaton:
        return Automaton(self.cards)

    @cached_property
    def tag_tree(self) -> TagTree:
        return TagTree(C.ORACLE["TAGS"])

    @cached_property
    def emb_model(self):
        return HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            encode_kwargs={"batch_size": 64, "normalize_embeddings": True},
        )

    # Vector Stores
    @cached_property
    def _chroma_client(self):
        return chromadb.PersistentClient(path=C.CHROMA_DB)

    @cached_property
    def rules_store(self):
        return Chroma(
            client=self._chroma_client,
            collection_name=C.CHROMA_COLLECTIONS["RULES"],
            embedding_function=self.emb_model
        )

    @cached_property
    def qa_store(self):
        return Chroma(
            client=self._chroma_client,
            collection_name=C.CHROMA_COLLECTIONS["STACKEX"],
            embedding_function=self.emb_model
        )



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