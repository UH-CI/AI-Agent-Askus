from embeddings.base import Embedder
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI
from openai.types import CreateEmbeddingResponse

class HuggingFaceEmbeddingAdapter(Embedder):
    def __init__(self, embedder: HuggingFaceEmbeddings):
        self.embedder = embedder

    def embed_query(self, text):
        return self.embedder.embed_query(text)

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
        response = self.client.embeddings.create(
            input=texts, model=self.model
        )
        return [d.embedding for d in response.data]

def from_hugging_face(embedder: HuggingFaceEmbeddings) -> Embedder:
    return HuggingFaceEmbeddingAdapter(embedder)

def from_open_ai(client: OpenAI, model: str) -> Embedder:
    return OpenAIEmbeddingAdapter(client, model)