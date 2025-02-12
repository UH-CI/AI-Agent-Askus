from langchain_core.document_loaders import BaseLoader
from langchain.text_splitter import TextSplitter
from embeddings.base import Embedder
from langchain_chroma import Chroma
from chromadb.api import API

def upload(
    chroma: Chroma,
    loader: BaseLoader,
    splitter: TextSplitter = None,
    batch_size: int = 10,
    reset: bool = False,
) -> list[str]:
    """
    Upload documents into a ChromaDB collection after optional splitting and embedding.

    Args:
        name (str): The name of the collection.
        loader (BaseLoader): Loader to load documents.
        embedder (Embedder): Embedder providing an embedding function.
        splitter (TextSplitter, optional): Text splitter for splitting document text.
        batch_size (int): The number of documents per upload batch.
        reset (bool): If True, clear the collection before uploading.
    """
 
    # If reset is True, delete all documents in the collection.
    if reset:
        chroma.reset_collection()

    # Load documents. If a splitter is provided, call loader.load_and_split,
    # otherwise fallback to loader.load.
    docs = loader.load_and_split(splitter) if splitter else loader.load()

    # Upload documents in batches.
    total_docs = len(docs)
    ids: list[str] = []
    for i in range(0, total_docs, batch_size):
        batch = docs[i : i + batch_size]
        batch_ids = chroma.add_documents(batch)
        ids += batch_ids
    
    return ids