import re
from pathlib import Path
from typing import Iterator

from bs4 import BeautifulSoup
from html2text import HTML2Text

from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader


class AskUsHtmlDirectoryLoader(BaseLoader):
    """
    Loader for HTML files in a directory that contain FAQ content.
    
    Each HTML file is expected to have elements with IDs:
    - "kb_article_question" for the question
    - "kb_article_text" for the answer

    The loader parses these elements, cleans the text, and yields a Document
    for each valid HTML file.
    """

    def __init__(self, dir_path: str):
        """
        Initializes the loader with the directory path containing HTML files.

        Args:
            dir_path: The path to the directory containing HTML files.
        """
        self.dir_path = Path(dir_path)
        self.html2text = HTML2Text()
        self.html2text.ignore_images = True

    def faq_html_parser(self, html: str) -> str:
        """
        Parses an HTML string to extract FAQ content (question and answer).

        Args:
            html: The HTML content as a string.

        Returns:
            A cleaned string combining the question and answer, or
            None if the expected elements are not found.
        """
        soup = BeautifulSoup(html, "lxml")
        question = soup.find(id="kb_article_question")
        answer = soup.find(id="kb_article_text")

        if not question or not answer:
            return None

        # Convert HTML to text using HTML2Text.
        question_text = self.html2text.handle(str(question))
        answer_text = self.html2text.handle(str(answer))

        combined_text = f"{question_text}\n{answer_text}"
        # Clean up extra newlines and whitespace.
        cleaned_text = re.sub(r'\n{2,}', '\n', combined_text.strip())

        return cleaned_text

    def lazy_load(self) -> Iterator[Document]:
        """
        Lazily loads and parses HTML files from the given directory.

        Yields:
            Document instances with parsed FAQ text as page_content and metadata
            containing the source URL.
        """
        for html_file_path in self.dir_path.glob("*.html"):
            try:
                with html_file_path.open("r", encoding="utf-8") as f:
                    html_content = f.read()
            except Exception as e:
                # Optionally log the error and continue to the next file.
                continue

            extracted = self.faq_html_parser(html_content)
            if not extracted:
                continue

            # Derive the source URL from the file name.
            # `Path.stem` automatically removes the file extension.
            source = f"https://www.hawaii.edu/askus/{html_file_path.stem}"

            yield Document(page_content=extracted, metadata={"source": source})
