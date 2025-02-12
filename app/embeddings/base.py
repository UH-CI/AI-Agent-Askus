from abc import ABC, abstractmethod
import chromadb

class Embedder(ABC, chromadb.EmbeddingFunction):
    """
    Interface for vector embedding.
    """
    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed query

        Args:
            text: Text to convert to vector embedding

        Returns:
            list[float]: A vector embedding
        """
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]
    
    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        return self.embed_documents(input)