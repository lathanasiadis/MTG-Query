from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from mtgquery.constants import chroma_colls, files
from mtgquery.state import State


def load_documents(dir_path: Path) -> list[Document]:
    docs: list[Document] = []
    for (root, _, dir_files) in dir_path.walk():
        for file in dir_files:
            file_path = Path(root).absolute().joinpath(file)
            with open(file_path, "r") as f:
                docs.append(Document(
                    page_content = f.read(),
                    metadata = {"source": str(file_path)}
                ))
    return docs

if __name__ == "__main__":
    print("Loading rules...")
    rule_docs = load_documents(files.RULES_DIR)
    print("Loading stack exchange QAs...")
    qa_docs = load_documents(files.STACKEX_DIR)

    rules_store = Chroma(
        collection_name=chroma_colls.RULES,
        embedding_function=State.emb_model,
        persist_directory=files.CHROMA_DB,
    )
    qa_store = Chroma(
        collection_name=chroma_colls.STACKEX,
        embedding_function=State.emb_model,
        persist_directory=files.CHROMA_DB
    )

    print("Adding rules to the vector store...")
    ids = rules_store.add_documents(documents=rule_docs)
    print("Adding stack exchange QAs to the vector store...")
    ids = qa_store.add_documents(documents=qa_docs)
