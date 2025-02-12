from db.chroma import utils
import unittest
from dotenv import load_dotenv
from chromadb import HttpClient
from embeddings import convert
from openai import OpenAI
from loaders.html import AskUsHtmlDirectoryLoader
from langchain_chroma import Chroma

import os

class TestChromaUtils(unittest.TestCase):
    def setUp(self):
        load_dotenv(override=True)
    
    def test_utils_upload(self):
        print("Testing Chroma Utils Upload")        
        embedder = convert.from_open_ai(OpenAI(), "text-embedding-3-large")
        http_client = HttpClient(os.getenv("CHROMA_HOST"), os.getenv("CHROMA_PORT"))
        chroma = Chroma(collection_name="test", embedding_function=embedder, client=http_client, collection_metadata={"hnsw:space": "cosine"})
        
        loader = AskUsHtmlDirectoryLoader("data/askus")

        utils.upload(chroma, loader, reset=True)
        self.assertEqual(len(chroma.get(where={})["ids"]), 9)
        
        utils.upload(chroma, loader, reset=False)
        self.assertEqual(len(chroma.get(where={})["ids"]), 18)
        
        utils.upload(chroma, loader, reset=True)
        self.assertEqual(len(chroma.get(where={})["ids"]), 9) 

if __name__ == "__main__":
    unittest.main()