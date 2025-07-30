import re
import unicodedata
import logging
os = __import__('os')
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from manoa_agent.embeddings.base import Embedder

class DummyEmbedder(Embedder):
    """A dummy embedder that returns random vectors for testing"""
    def __init__(self, dim=1536):  # OpenAI default dimension
        self.dim = dim
        logger.warning("Using DummyEmbedder! This should only be used for testing.")
        
    def embed_query(self, text):
        return list(np.random.rand(self.dim).astype(float))
        
    def embed_documents(self, texts):
        return [list(np.random.rand(self.dim).astype(float)) for _ in texts]

try:
    from openai import OpenAI
    from openai.types import CreateEmbeddingResponse
    
    class OpenAIEmbeddingAdapter(Embedder):
        def __init__(self, client: OpenAI, model: str):
            self.client = client
            self.model = model
            
            # Verify API key is set
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY is not set in environment. Embeddings will fail.")
    
        def _sanitize_text(self, text):
            """Sanitize text to avoid encoding issues"""
            # Handle None or empty strings
            if not text:
                return ""
                
            # Convert to string if not already
            if not isinstance(text, str):
                text = str(text)
                
            # Replace problematic Unicode characters
            text = text.replace('\u2026', '...')  # ellipsis
            text = text.replace('\u2013', '-')    # en dash
            text = text.replace('\u2014', '--')   # em dash
            text = text.replace('\u2018', "'")    # left single quote
            text = text.replace('\u2019', "'")    # right single quote
            text = text.replace('\u201c', '"')    # left double quote
            text = text.replace('\u201d', '"')    # right double quote
            
            # Normalize and strip control characters
            text = unicodedata.normalize('NFKD', text)
            text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
            
            return text
    
        def _sanitize_texts(self, texts):
            """Sanitize a list of texts"""
            if not texts:
                return [""]
            if isinstance(texts, str):
                return self._sanitize_text(texts)
            return [self._sanitize_text(t) for t in texts]
    
        def embed_query(self, text):
            try:
                text = self._sanitize_text(text)
                response = self.client.embeddings.create(
                    input=text, model=self.model
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"Error embedding query: {e}")
                # Return dummy embedding for graceful degradation
                return list(np.random.rand(1536).astype(float))
    
        def embed_documents(self, texts):
            try:
                texts = self._sanitize_texts(texts)
                # Process in smaller batches to avoid any potential issues
                batch_size = 16
                all_embeddings = []
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    response = self.client.embeddings.create(input=batch, model=self.model)
                    all_embeddings.extend([d.embedding for d in response.data])
                    
                return all_embeddings
            except Exception as e:
                logger.error(f"Error embedding documents: {e}")
                # Return dummy embeddings for graceful degradation
                return [list(np.random.rand(1536).astype(float)) for _ in texts]

except ImportError:
    logger.warning("OpenAI package not available. Using DummyEmbedder.")
    OpenAIEmbeddingAdapter = DummyEmbedder  # Fallback to dummy embedder


def from_open_ai(client=None, model="text-embedding-3-large") -> Embedder:
    """Create an OpenAI embedding adapter, or fallback to dummy embedder if unavailable"""
    try:
        if client is None:
            try:
                # Try to create a client if not provided
                from openai import OpenAI
                client = OpenAI()
            except Exception as e:
                logger.error(f"Could not create OpenAI client: {e}")
                return DummyEmbedder()
        
        return OpenAIEmbeddingAdapter(client, model)
    except Exception as e:
        logger.error(f"Error creating OpenAI embedding adapter: {e}")
        return DummyEmbedder()
