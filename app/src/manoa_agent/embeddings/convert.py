import re
import unicodedata

from openai import OpenAI
from openai.types import CreateEmbeddingResponse

from manoa_agent.embeddings.base import Embedder


class OpenAIEmbeddingAdapter(Embedder):
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def _sanitize_text(self, text):
        """Sanitize text to avoid encoding issues"""
        # Replace problematic Unicode characters with ASCII equivalents
        text = text.replace('\u2026', '...')  # Replace ellipsis
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        # Strip control characters
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
        return text

    def _sanitize_texts(self, texts):
        """Sanitize a list of texts"""
        if isinstance(texts, str):
            return self._sanitize_text(texts)
        return [self._sanitize_text(t) for t in texts]

    def embed_query(self, text):
        text = self._sanitize_text(text)
        response: CreateEmbeddingResponse = self.client.embeddings.create(
            input=text, model=self.model
        )
        return response.data[0].embedding

    def embed_documents(self, texts):
        texts = self._sanitize_texts(texts)
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [d.embedding for d in response.data]


def from_open_ai(client: OpenAI, model: str) -> Embedder:
    return OpenAIEmbeddingAdapter(client, model)
