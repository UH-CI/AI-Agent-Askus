from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader
from typing import Iterator
from glob import glob

class HTMLDirectoryLoader(BaseLoader):
    def __init__(self, dir_path: str, html_parser):
        self.html_parser = html_parser
        self.dir_path = dir_path

    def lazy_load(self) -> Iterator[Document]:
        for path in glob(f'{self.dir_path}/*.html'):
            with open(path, "r") as f:
                html_file = f.read()
            extracted = self.html_parser(html_file)

            if not extracted:
                continue
            
            source = path.removesuffix(".html")
            source = source.split("/")[-1]
            source = f"https://www.hawaii.edu/askus/{source}"

            yield Document(page_content=extracted, metadata={"source": source})