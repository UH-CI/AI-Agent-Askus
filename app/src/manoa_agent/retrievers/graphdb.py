from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from neo4j_graphrag.retrievers import VectorRetriever
from pydantic import ConfigDict


class GraphVectorRetriever(BaseRetriever):
    model_config = ConfigDict(extra="allow")  # This sets the class-level config

    def __init__(self, retriever: VectorRetriever):
        super().__init__()
        self.retriever = retriever

    def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        results = self.retriever.get_search_results(query_text=query)
        results_text = [record['node']['text'] for record in results.records]
        return [Document(page_content=text) for text in results_text]
