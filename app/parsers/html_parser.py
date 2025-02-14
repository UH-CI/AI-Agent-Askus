from bs4 import BeautifulSoup
from parsers.base import Parser
from html2text import HTML2Text

class HTMLParser(Parser):
    def __init__(self, html2text: HTML2Text, ids: list[str] = [], tags: list[str] = []):
        self.h = html2text
        self.ids = ids
        self.tags = tags

    def parse(self, text: str) -> str:
        soup = BeautifulSoup(text, "html.parser")

        # First, look for elements by id in provided order
        for element_id in self.ids:
            element = soup.find(id=element_id)
            if element:
                return self.h.handle(str(element))

        # Next, look for the first available element by tag name
        for tag in self.tags:
            element = soup.find(tag)
            if element:
                return self.h.handle(str(element))

        # Fallback: process the entire HTML
        return self.h.handle(text)
