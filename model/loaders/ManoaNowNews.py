from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.document_loaders import BaseLoader
from html2text import HTML2Text
import requests
from typing import Iterator, List
from bs4 import BeautifulSoup

class ManoaNowNewsLoader(BaseLoader):
    def __init__(self) -> None:
        pass
    
    def lazy_load(self) -> Iterator[Document]:
        base_url = "https://www.manoanow.org/kaleo/news/"
        response = requests.get(base_url)

        h = HTML2Text()

        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        news = soup.find_all("article")

        for article in news:
            content = h.handle(str(article))
            yield Document(page_content=f"Current News: {content}", metadata={"source": "https://www.manoanow.org/kaleo/news/"})
        
class ManoaNowNewsRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        manoa_now_news_loader = ManoaNowNewsLoader()
        db = InMemoryVectorStore(self.embedding_function)
        db.add_documents(list(manoa_now_news_loader.lazy_load()))
        return db.similarity_search(query, k=2)