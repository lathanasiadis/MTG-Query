import os
from langchain_core.documents import Document
from langchain_chroma import Chroma

from constants import Constants as C
from data import State

def load_documents(dir_path: str) -> list[Document]:
    docs = []
    for (root, dirs, files) in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, "r") as f:
                docs.append(Document(
                    page_content = f.read(),
                    metadata = {"source": file_path}
                ))
    return docs

if __name__ == "__main__":
    print("Loading rules...")
    rule_docs = load_documents(C.RULES_DIR)
    print("Loading stack exchange QAs...")
    qa_docs = load_documents(C.STACKEX_DIR)

    rules_store = Chroma(
        collection_name=C.CHROMA_COLLECTIONS["RULES"],
        embedding_function=State.emb_model,
        persist_directory=C.CHROMA_DB,
    )
    qa_store = Chroma(
        collection_name=C.CHROMA_COLLECTIONS["STACKEX"],
        embedding_function=State.emb_model,
        persist_directory=C.CHROMA_DB
    )

    print("Adding rules to the vector store...")
    ids = rules_store.add_documents(documents=rule_docs)
    print("Adding stack exchange QAs to the vector store...")
    ids = qa_store.add_documents(documents=qa_docs)
