from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader
from typing import Iterator
import json

class JSONFileLoader(BaseLoader):
    def __init__(self, json_path: str, json_parser):
        self.json_path = json_path
        self.json_parser = json_parser

    def lazy_load(self) -> Iterator[Document]:
        with open(self.json_path, "r") as f:
            json_data = json.load(f)
        
        for d in json_data:
            parsed = self.json_parser(d)

            yield Document(
                page_content=parsed["page_content"],
                metadata=parsed["metadata"]
            )