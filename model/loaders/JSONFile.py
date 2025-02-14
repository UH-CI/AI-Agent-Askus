from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader
from typing import Iterator
import json


class JSONFileLoader(BaseLoader):
    """
    A JSON file loader that parses a file with the following format:
    [
        {
            "url": "https://example.com",
            "extracted": "Extracted text from the page..."
        },
        ...
    ]
    It creates a Document for each entry, using "extracted" as the content and
    "url" as metadata.
    """

    def __init__(self, json_path: str):
        self.json_path = json_path

    def lazy_load(self) -> Iterator[Document]:
        with open(self.json_path, "r") as f:
            json_data = json.load(f)

        for doc in json_data:
            yield Document(
                page_content=doc["extracted"],
                metadata={"source": doc["url"]}
            )
