from bs4 import BeautifulSoup
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from html2text import HTML2Text
from loaders.HTMLDirectory import HTMLDirectoryLoader
import re
import yaml

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

model_name = config["embedding"]
model_kwargs = {'device': 'cuda', "trust_remote_code": True}

embedding_model = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
)

vector_store_faq = Chroma(
    collection_name="its_faq",
    persist_directory="db",
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

vector_store_policies = Chroma(
    collection_name="uh_policies",
    persist_directory="db",
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

vector_store_faq.reset_collection()
vector_store_policies.reset_collection()

text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=8000,
    chunk_overlap=100
)

h = HTML2Text()
h.ignore_images = True

def faq_html_parser(html):
    soup = BeautifulSoup(html, features="lxml")
    question = soup.find(id="kb_article_question")
    answer = soup.find(id="kb_article_text")

    if not question or not answer:
        return None
    
    question = h.handle(str(question))
    answer = h.handle(str(answer))

    qa = f"{question}\n{answer}"
    removed_repeating_newlines = re.sub(r'\n{2,}', '\n', qa)

    return removed_repeating_newlines

faq_html_loader = HTMLDirectoryLoader("../web-scraper/faq-archive", faq_html_parser)
faq_documents = list(faq_html_loader.lazy_load())
faq_split_documents = text_splitter.split_documents(faq_documents)

# vector_store_faq.add_documents([Document(page_content="This is a test document for duo mobile", metadata={"id": "test_doc_1"})])

batch_size = 20  # Adjust this value based on your GPU memory
for i in range(0, len(faq_split_documents), batch_size):
    print(f"Adding batch {i + 1} to {i + batch_size}")
    batch = faq_split_documents[i:i + batch_size]
    vector_store_faq.add_documents(batch)

# print(f"{len(faq_split_documents)} faq docs in vector store")
print(vector_store_faq.similarity_search("duo mobile"))