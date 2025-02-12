from db.chroma import utils
import unittest
from dotenv import load_dotenv
from chromadb import HttpClient
from embeddings import convert
from openai import OpenAI
from loaders.html import AskUsHtmlDirectoryLoader
from langchain_chroma import Chroma

import os

class TestAskUsHtmlDirectoryLoader(unittest.TestCase):
    def setUp(self):
        load_dotenv(override=True)
    
    def test_html_loader(self):
        print("Testing AskUs HTML Directory Loader")
        loader = AskUsHtmlDirectoryLoader("data/askus")
        self.assertEqual(len(loader.load()), 9)

if __name__ == "__main__":
    unittest.main()