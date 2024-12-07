import argparse
from bs4 import BeautifulSoup
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from html2text import HTML2Text
from loaders.HTMLDirectory import HTMLDirectoryLoader
import re
import yaml
from loaders.JSONFile import JSONFileLoader

def setup_embeddings():
    with open("config.yml", "r") as f:
        config = yaml.safe_load(f)

    model_name = config["embedding"]
    model_kwargs = {'device': 'cuda', "trust_remote_code": True}

    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
    )

def reload_faq(embedding_model, batch_size):
    vector_store_faq = Chroma(
        collection_name="its_faq",
        persist_directory="db",
        embedding_function=embedding_model,
        collection_metadata={"hnsw:space": "cosine"}
    )
    vector_store_faq.reset_collection()

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

    for i in range(0, len(faq_split_documents), batch_size):
        print(f"Adding FAQ batch {i + 1} to {i + batch_size}")
        batch = faq_split_documents[i:i + batch_size]
        vector_store_faq.add_documents(batch)

def reload_policies(embedding_model, batch_size):
    vector_store_policies = Chroma(
        collection_name="uh_policies",
        persist_directory="db",
        embedding_function=embedding_model,
        collection_metadata={"hnsw:space": "cosine"}
    )
    vector_store_policies.reset_collection()

    policy_docs = list(JSONFileLoader("data/policies.json").lazy_load())

    for i in range(0, len(policy_docs), batch_size):
        print(f"Adding policies batch {i + 1} to {i + batch_size}")
        batch = policy_docs[i:i + batch_size]
        vector_store_policies.add_documents(batch)

def main():
    parser = argparse.ArgumentParser(description='Reload vector databases for FAQ and policies')
    parser.add_argument('--faq', action='store_true', help='Reload the FAQ database')
    parser.add_argument('--policies', action='store_true', help='Reload the policies database')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size for processing documents')
    
    args = parser.parse_args()
    
    if not (args.faq or args.policies):
        parser.error("At least one of --faq or --policies must be specified")

    embedding_model = setup_embeddings()
    
    if args.faq:
        reload_faq(embedding_model, args.batch_size)
    
    if args.policies:
        reload_policies(embedding_model, args.batch_size)

if __name__ == "__main__":
    main()