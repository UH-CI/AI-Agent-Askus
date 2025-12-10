import os

from chromadb import HttpClient
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain_chroma import Chroma
from openai import OpenAI

from manoa_agent.db.chroma import utils
from manoa_agent.embeddings.convert import OpenAIEmbeddingAdapter
from manoa_agent.loaders.html import HtmlDirectoryLoader
from manoa_agent.loaders.json_loader import JSONFileLoader

load_dotenv(override=True)

embedder = OpenAIEmbeddingAdapter(OpenAI(), "text-embedding-3-large")
http_client = HttpClient(host=os.getenv("CHROMA_HOST"), port=os.getenv("CHROMA_PORT"))

general_collection = Chroma(
    collection_name="general_faq",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"},
)

print("🗄️ Starting database loading process...")

text_splitter = CharacterTextSplitter(
    separator="\n", chunk_size=500, chunk_overlap=200
)

# Load FAQ data (required)
print("📚 Loading FAQ data...")
faq_loader = HtmlDirectoryLoader("data/askus")
utils.upload(general_collection, faq_loader, text_splitter, reset=True, batch_size=30)
print("✅ FAQ data loaded successfully")

# Load UH policies (required)
print("📋 Loading UH policies...")
policies_path = "data/json/policies.json"
if os.path.exists(policies_path):
    json_loader = JSONFileLoader(policies_path)
    utils.upload(general_collection, json_loader, text_splitter, reset=False, batch_size=30)
    print("✅ UH policies loaded successfully")
else:
    print(f"⚠️  Warning: {policies_path} not found, skipping...")

# Load TeamDynamix knowledge base articles (optional)
print("🔧 Loading TeamDynamix knowledge base articles...")
teamdynamix_paths = [
    "../web-scraper/data/kb_articles_extracted.json",  # Original path
    "/app/../web-scraper/data/kb_articles_extracted.json",  # Docker absolute path
    "data/json/teamdynamix.json"  # Alternative local path
]

teamdynamix_loaded = False
for tdx_path in teamdynamix_paths:
    if os.path.exists(tdx_path):
        try:
            print(f"📁 Found TeamDynamix data at: {tdx_path}")
            teamdynamix_loader = JSONFileLoader(tdx_path)
            utils.upload(general_collection, teamdynamix_loader, text_splitter, reset=False, batch_size=30)
            print("✅ TeamDynamix data loaded successfully")
            teamdynamix_loaded = True
            break
        except Exception as e:
            print(f"⚠️  Failed to load {tdx_path}: {e}")
            continue

if not teamdynamix_loaded:
    print("⚠️  Warning: TeamDynamix data not found at any expected location, skipping...")
    print("   Searched paths:")
    for path in teamdynamix_paths:
        print(f"   - {path}")

print("🎉 Database loading completed!")


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
