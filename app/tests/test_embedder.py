import unittest

import numpy as np
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI

from manoa_agent.embeddings import convert
from manoa_agent.embeddings.base import Embedder


def cosine_similarity(a, b):
    """Compute the cosine similarity between two vectors."""
    a, b = np.array(a), np.array(b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a * norm_b == 0:
        return 0
    return dot_product / (norm_a * norm_b)


class TestAdapters(unittest.TestCase):
    def setUp(self):
        load_dotenv(override=True)

    def run_embedding_test(self, embedder: Embedder):
        """
        Common helper method to execute embedding tests.
        """
        embedding = embedder.embed_query("Cold")
        embeddings = embedder.embed_documents(["Cold", "Hot"])

        # Ensure we get list outputs.
        self.assertIsInstance(embedding, list)
        self.assertIsInstance(embeddings, list)

        # Calculate cosine similarities.
        cos_sim_same = cosine_similarity(embedding, embeddings[0])
        cos_sim_diff = cosine_similarity(embedding, embeddings[1])

        # For the same input ("Cold"), similarity should be near 1.
        self.assertGreaterEqual(
            cos_sim_same, 0.99, "Cosine similarity for same input is too low."
        )
        # For different input ("Hot"), the cosine similarity should be lower.
        self.assertLessEqual(
            cos_sim_diff, 0.8, "Cosine similarity for different input is too high."
        )

    def test_huggingface_adapter(self):
        print("Testing Huggingface Embedding Adapter")
        model_kwargs = {"device": "cuda", "trust_remote_code": True}

        embedding_client = HuggingFaceEmbeddings(
            model_name="dunzhang/stella_en_1.5B_v5", model_kwargs=model_kwargs
        )

        embedder = convert.from_hugging_face(embedding_client)
        self.run_embedding_test(embedder)

    def test_openai_adapter(self):
        print("Testing OpenAI Embedding Adapter")
        embedding_client = OpenAI()
        embedder = convert.from_open_ai(embedding_client, "text-embedding-3-large")
        self.run_embedding_test(embedder)


if __name__ == "__main__":
    unittest.main()
