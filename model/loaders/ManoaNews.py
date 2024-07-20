from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.document_loaders import BaseLoader
import requests
from typing import Iterator, List
from bs4 import BeautifulSoup

class ManoaNewsLoader(BaseLoader):
    def __init__(self) -> None:
        pass

    def lazy_load(self) -> Iterator[Document]:
        base_url = "https://manoa.hawaii.edu/news/archive.php"
        response = requests.get(base_url)

        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        news = soup.find("news")
        latest = news.find("div")
        title = latest.text
        news_url = base_url.replace("archive", "article") + "?aId=13339"

        yield Document(page_content=f"Current News: {title}\nFor more information, visit this url: {news_url}", metadata={"source": news_url, "title": title})
        
class ManoaNewsRetriever(BaseRetriever):
    def __init__(self, embedding_function):
        self.embedding_function = embedding_function

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        manoa_news_loader = ManoaNewsLoader()
        db = InMemoryVectorStore(self.embedding_function)
        db.add_documents(list(manoa_news_loader.lazy_load()))
        return db.similarity_search(query, k=4)