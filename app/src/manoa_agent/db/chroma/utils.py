from langchain.text_splitter import TextSplitter
from langchain_chroma import Chroma
from langchain_core.document_loaders import BaseLoader
from tqdm import tqdm  # progress bar
import uuid


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

    # Load documents first without splitting to get full documents
    full_docs = loader.load()
    
    # Create a mapping of full documents with unique IDs
    doc_id_mapping = {}
    for doc in full_docs:
        doc_id = str(uuid.uuid4())
        doc_id_mapping[doc.page_content] = {
            "doc_id": doc_id,
            "full_content": doc.page_content,
            "metadata": doc.metadata
        }
    
    # Now split documents if splitter is provided
    if splitter:
        docs = loader.load_and_split(splitter)
        # Add full document content and unique ID to each chunk's metadata
        for doc in docs:
            # Find the original full document this chunk came from
            for full_content, doc_info in doc_id_mapping.items():
                if doc.page_content in full_content:
                    doc.metadata["doc_id"] = doc_info["doc_id"]
                    doc.metadata["full_document"] = doc_info["full_content"]
                    break
    else:
        docs = full_docs
        # Add unique IDs to non-split documents
        for doc in docs:
            doc_info = doc_id_mapping[doc.page_content]
            doc.metadata["doc_id"] = doc_info["doc_id"]
            doc.metadata["full_document"] = doc.page_content

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
