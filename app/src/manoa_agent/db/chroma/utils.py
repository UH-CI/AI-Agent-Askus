from chromadb.api import API
from langchain.text_splitter import TextSplitter
from langchain_chroma import Chroma
from langchain_core.document_loaders import BaseLoader
from tqdm import tqdm  # progress bar


def upload(
    chroma: Chroma,
    loader: BaseLoader,
    splitter: TextSplitter = None,
    batch_size: int = -1,
    reset: bool = False,
) -> list[str]:
    """
    Upload documents into a ChromaDB collection after optional splitting
    and embedding.

    Args:
        chroma (Chroma): An instance of the ChromaDB wrapper.
        loader (BaseLoader): Loader to load documents.
        splitter (TextSplitter, optional): Text splitter for splitting document
            text.
        batch_size (int): The number of documents per upload batch. Use -1 for
            no batching.
        reset (bool): If True, clear the collection before uploading.
    Returns:
        list[str]: A list of document IDs after upload.
    """

    # If reset is True, clear the collection.
    if reset:
        chroma.reset_collection()

    # Load documents. If a splitter is provided, use loader.load_and_split,
    # otherwise, fallback to loader.load.
    docs = loader.load_and_split(splitter) if splitter else loader.load()

    # Upload documents by batches.
    if batch_size > 0:
        total_docs = len(docs)
        ids: list[str] = []
        # Wrap the loop with tqdm to create a progress bar.
        for i in tqdm(
            range(0, total_docs, batch_size), desc="Uploading documents in batches"
        ):
            batch = docs[i : i + batch_size]
            batch_ids = chroma.add_documents(batch)
            ids.extend(batch_ids)
        return ids

    # If batch_size is -1, upload all documents at once.
    if batch_size == -1:
        return chroma.add_documents(docs)
