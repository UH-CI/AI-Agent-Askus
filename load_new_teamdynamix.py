#!/usr/bin/env python3
"""
Load only the new TeamDynamix data from web-scraper into the existing ChromaDB
"""

import os
import sys
sys.path.append('/home/exouser/AI-Agent-Askus/app/src')

from chromadb import HttpClient
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain_chroma import Chroma
from openai import OpenAI

from manoa_agent.db.chroma import utils
from manoa_agent.embeddings.convert import OpenAIEmbeddingAdapter
from manoa_agent.loaders.json_loader import JSONFileLoader

load_dotenv()

def load_new_teamdynamix_data():
    print("🔄 Loading NEW TeamDynamix data only...")
    print("=" * 60)
    
    # Initialize ChromaDB connection
    embedder = OpenAIEmbeddingAdapter(OpenAI(), "text-embedding-3-large")
    http_client = HttpClient(host=os.getenv("CHROMA_HOST"), port=os.getenv("CHROMA_PORT"))
    
    general_collection = Chroma(
        collection_name="general_faq",
        client=http_client,
        embedding_function=embedder,
        collection_metadata={"hnsw:space": "cosine"},
    )
    
    # Check current collection size
    try:
        collection_count = general_collection._collection.count()
        print(f"📊 Current collection size: {collection_count} documents")
    except Exception as e:
        print(f"❌ Error checking collection: {e}")
        return False
    
    # Initialize text splitter (same as in load_db.py)
    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=500, chunk_overlap=200
    )
    
    # Load NEW TeamDynamix data from web-scraper
    teamdynamix_file = "/home/exouser/AI-Agent-Askus/web-scraper/data/kb_articles_extracted.json"
    
    if not os.path.exists(teamdynamix_file):
        print(f"❌ TeamDynamix file not found: {teamdynamix_file}")
        return False
    
    print(f"📁 Loading NEW TeamDynamix data from: {teamdynamix_file}")
    
    try:
        # Create JSON loader
        teamdynamix_loader = JSONFileLoader(teamdynamix_file)
        
        # Load documents to check how many we have
        docs = teamdynamix_loader.load()
        print(f"📋 Loaded {len(docs)} NEW TeamDynamix documents")
        
        # Show sample of what we're loading
        if docs:
            print(f"\n📝 Sample document:")
            sample_doc = docs[0]
            print(f"   Source: {sample_doc.metadata.get('source', 'Unknown')}")
            print(f"   Content preview: {sample_doc.page_content[:200]}...")
        
        # First, let's remove any existing TeamDynamix data to avoid duplicates
        print(f"\n🧹 Removing old TeamDynamix data...")
        
        # Get all documents and filter out TeamDynamix ones
        all_docs = general_collection.get()
        teamdx_ids = []
        
        if 'metadatas' in all_docs and all_docs['metadatas']:
            for i, metadata in enumerate(all_docs['metadatas']):
                if metadata and 'source' in metadata:
                    source = metadata['source']
                    if 'teamdynamix.com' in source:
                        teamdx_ids.append(all_docs['ids'][i])
        
        if teamdx_ids:
            print(f"🗑️  Removing {len(teamdx_ids)} old TeamDynamix documents...")
            general_collection.delete(ids=teamdx_ids)
            
            # Check new count
            new_count = general_collection._collection.count()
            print(f"📊 Collection size after cleanup: {new_count} documents")
        else:
            print("ℹ️  No existing TeamDynamix data found to remove")
        
        # Upload NEW TeamDynamix data
        print(f"\n🔄 Uploading NEW TeamDynamix documents to ChromaDB...")
        doc_ids = utils.upload(
            general_collection, 
            teamdynamix_loader, 
            text_splitter, 
            reset=False,  # Don't reset, just add to existing collection
            batch_size=30
        )
        
        print(f"✅ Successfully uploaded {len(doc_ids)} NEW document chunks")
        
        # Check final collection size
        final_collection_count = general_collection._collection.count()
        print(f"📊 Final collection size: {final_collection_count} documents")
        
        # Test if NEW TeamDynamix content is now retrievable
        print(f"\n🔍 Testing retrieval of NEW TeamDynamix content...")
        test_queries = [
            "How to install Spirion software",
            "eduroam macOS setup", 
            "Google Consumer Apps"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            search_results = general_collection.similarity_search(query, k=3)
            
            teamdx_results = []
            for result in search_results:
                source = result.metadata.get('source', 'Unknown')
                if 'teamdynamix.com' in source:
                    teamdx_results.append(result)
            
            if teamdx_results:
                print(f"   ✅ Found {len(teamdx_results)} NEW TeamDynamix results")
                for i, result in enumerate(teamdx_results, 1):
                    source = result.metadata.get('source', 'Unknown')
                    if 'ID=' in source:
                        article_id = source.split('ID=')[1].split('&')[0] if '&' in source.split('ID=')[1] else source.split('ID=')[1]
                        print(f"      {i}. Article ID: {article_id}")
                    else:
                        print(f"      {i}. {source}")
            else:
                print(f"   ❌ No NEW TeamDynamix results found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during loading: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = load_new_teamdynamix_data()
    if success:
        print(f"\n🎉 NEW TeamDynamix data loading completed successfully!")
    else:
        print(f"\n💥 NEW TeamDynamix data loading failed!")
