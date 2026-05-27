from openai import OpenAI
from openai.types import CreateEmbeddingResponse
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from manoa_agent.embeddings.base import Embedder


class OpenAIEmbeddingAdapter(Embedder):
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def embed_query(self, text):
        response: CreateEmbeddingResponse = self.client.embeddings.create(
            input=text, model=self.model
        )
        return response.data[0].embedding

    def embed_documents(self, texts):
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [d.embedding for d in response.data]


def from_open_ai(client: OpenAI, model: str) -> Embedder:
    return OpenAIEmbeddingAdapter(client, model)


class GoogleEmbeddingAdapter(Embedder):
    def __init__(self, api_key: str, model: str):
        self._embeddings = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)

    def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)


def from_google(api_key: str, model: str = "gemini-embedding-001") -> Embedder:
    return GoogleEmbeddingAdapter(api_key, model)
