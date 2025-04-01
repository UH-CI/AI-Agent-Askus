from manoa_agent.embeddings.convert import OpenAIEmbeddingAdapter
from openai import OpenAI
from manoa_agent.db.chroma import utils
from chromadb import HttpClient
from langchain_chroma import Chroma
from manoa_agent.loaders.html import HtmlDirectoryLoader
from manoa_agent.loaders.json_loader import JSONFileLoader
from langchain.text_splitter import CharacterTextSplitter

from dotenv import load_dotenv
import os

load_dotenv(override=True)

embedder = OpenAIEmbeddingAdapter(OpenAI(), "text-embedding-3-large")
http_client = HttpClient(host=os.getenv("CHROMA_HOST"), port=os.getenv("CHROMA_PORT"))

general_collection = Chroma(
    collection_name="general_faq",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"}
)


text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=8000,
    chunk_overlap=100
)

faq_loader = HtmlDirectoryLoader("data/askus")
utils.upload(general_collection, faq_loader, text_splitter, reset=False, batch_size=30)

json_loader = JSONFileLoader("data/json/policies.json")
utils.upload(general_collection, json_loader, text_splitter, reset=False, batch_size=30)





# its_faq_collection = Chroma(
#     collection_name="its_faq",
#     client=http_client,
#     embedding_function=embedder,
#     collection_metadata={"hnsw:space": "cosine"}
# )

# policies_collection = Chroma(
#     collection_name="uh_policies",
#     client=http_client,
#     embedding_function=embedder,
#     collection_metadata={"hnsw:space": "cosine"}
# )

# faq_loader = HtmlDirectoryLoader("data/askus")
# utils.upload(its_faq_collection, faq_loader, text_splitter, reset=True, batch_size=30)

# json_loader = JSONFileLoader("data/json/policies.json")
# utils.upload(policies_collection, json_loader, text_splitter, reset=True, batch_size=30)

# json_loader = JSONFileLoader("data/json/hawaii.edu.json")
# utils.upload(general_collection, json_loader, text_splitter, reset=True, batch_size=30)