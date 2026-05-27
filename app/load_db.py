import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chromadb import HttpClient
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain_chroma import Chroma

from manoa_agent.db.chroma import utils
from manoa_agent.embeddings import convert
from manoa_agent.loaders.html import HtmlDirectoryLoader
from manoa_agent.loaders.json_loader import JSONFileLoader

load_dotenv(override=True)

embedder = convert.from_google(os.getenv("GEMINI_API_KEY"))
http_client = HttpClient(host=os.getenv("CHROMA_HOST"), port=os.getenv("CHROMA_PORT"))

for col in ["its_faq", "uh_policies", "general_faq", "predefined"]:
    try:
        http_client.delete_collection(col)
        print(f"Deleted collection: {col}")
    except Exception:
        pass

its_faq_collection = Chroma(
    collection_name="its_faq",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"},
)

policies_collection = Chroma(
    collection_name="uh_policies",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"},
)

general_collection = Chroma(
    collection_name="general_faq",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"},
)

text_splitter = CharacterTextSplitter(
    separator="\n", chunk_size=8000, chunk_overlap=100
)

faq_loader = HtmlDirectoryLoader("data/askus")
utils.upload(its_faq_collection, faq_loader, text_splitter, reset=True, batch_size=30)

json_loader = JSONFileLoader("data/json/policies.json")
utils.upload(policies_collection, json_loader, text_splitter, reset=True, batch_size=30)

json_loader = JSONFileLoader("data/json/hawaii.edu.json")
utils.upload(general_collection, json_loader, text_splitter, reset=True, batch_size=30)
