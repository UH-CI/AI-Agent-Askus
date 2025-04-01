import requests

from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader
from typing import Iterator, List
from manoa_agent.parsers.html_parser import HTMLParser

class WebLoader(BaseLoader):
    """
    A Web loader that will take in a URL, fetch the page HTML using requests,
    and convert it to a document using the provided HTMLParser.
    """

    def __init__(self, urls: List[str], html_parser: HTMLParser):
        self.urls = urls
        self.html_parser = html_parser

    def lazy_load(self) -> Iterator[Document]:
        for url in self.urls:
            response = requests.get(url)
            response.raise_for_status()  # Ensure the request was successful
            html_content = response.text

            # Use the provided HTMLParser to process the HTML
            parsed_content = self.html_parser.parse(html_content)

            yield Document(
                page_content=parsed_content,
                metadata={"source": url}
            )