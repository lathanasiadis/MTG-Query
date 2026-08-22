from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from mtgquery.constants import chroma_colls, files
from mtgquery.state import State


def load_documents(
    dir_path: Path,
    id_prefix: str | None = None,
    rule_ids: bool = False
) -> tuple[list[Document], list[str]]:

    assert rule_ids or id_prefix is not None, "[ERROR] load_rules: supply id_prefix when embedding something other than rules!"

    docs: list[Document] = []
    ids: list[str] = []
    i = 0
    for (root, _, dir_files) in dir_path.walk():
        for file in dir_files:
            parts = file.split(".")
            if rule_ids:
                if "701" in file or "702" in file:
                    ids.append(f"r{parts[0]}.{parts[1]}")
                else:
                    ids.append(f"r{parts[0]}")
            else:
                ids.append(f"{id_prefix}{i:04d}")
            file_path = Path(root).absolute().joinpath(file)
            with open(file_path, "r") as f:
                docs.append(Document(
                    page_content = f.read(),
                    metadata = {
                        "source": str(file_path)
                    }
                ))
    return (docs, ids)


if __name__ == "__main__":
    print("Loading rules...")
    rule_docs, rule_ids = load_documents(files.RULES_DIR, rule_ids=True)
    # print("Loading stack exchange QAs...")
    # qa_docs = load_qa(files.STACKEX_DIR, id_prefix="s")

    rules_store = Chroma(
        collection_name=chroma_colls.RULES,
        embedding_function=State.emb_model,
        persist_directory=files.CHROMA_DB,
        collection_metadata={"hnsw:space": "cosine"}
    )
    # qa_store = Chroma(
    #     collection_name=chroma_colls.STACKEX,
    #     embedding_function=State.emb_model,
    #     persist_directory=files.CHROMA_DB
    # )

    print("Adding rules to the vector store...")
    ids = rules_store.add_documents(documents=rule_docs, ids=rule_ids)
    # print("Adding stack exchange QAs to the vector store...")
    # ids = qa_store.add_documents(documents=qa_docs)
