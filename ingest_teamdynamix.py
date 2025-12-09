#!/usr/bin/env python3
"""
Ingest TeamDynamix data into ChromaDB
"""

import os
from chromadb import HttpClient
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain_chroma import Chroma
from openai import OpenAI
import sys
sys.path.append('/home/exouser/AI-Agent-Askus/app/src')

from manoa_agent.db.chroma import utils
from manoa_agent.embeddings.convert import OpenAIEmbeddingAdapter
from manoa_agent.loaders.json_loader import JSONFileLoader

load_dotenv(override=True)

def ingest_teamdynamix_data():
    print("🔄 Starting TeamDynamix data ingestion...")
    print("=" * 80)
    
    # Initialize ChromaDB connection
    embedder = OpenAIEmbeddingAdapter(OpenAI(), "text-embedding-3-large")
    http_client = HttpClient(host=os.getenv("CHROMA_HOST"), port=os.getenv("CHROMA_PORT"))
    
    general_collection = Chroma(
        collection_name="general_faq",
        client=http_client,
        embedding_function=embedder,
        collection_metadata={"hnsw:space": "cosine"},
    )
    
    # Initialize text splitter (same as in load_db.py)
    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=500, chunk_overlap=200
    )
    
    # Check current collection status
    try:
        collection_count = general_collection._collection.count()
        print(f"📊 Current collection size: {collection_count} documents")
    except Exception as e:
        print(f"❌ Error checking collection: {e}")
        return False
    
    # Load TeamDynamix data from the web-scraper directory (the correct dataset)
    teamdynamix_file = "/home/exouser/AI-Agent-Askus/web-scraper/data/kb_articles_extracted.json"
    
    if not os.path.exists(teamdynamix_file):
        print(f"❌ TeamDynamix file not found: {teamdynamix_file}")
        return False
    
    print(f"📁 Loading TeamDynamix data from: {teamdynamix_file}")
    
    try:
        # Create JSON loader
        teamdynamix_loader = JSONFileLoader(teamdynamix_file)
        
        # Load documents to check how many we have
        docs = teamdynamix_loader.load()
        print(f"📋 Loaded {len(docs)} TeamDynamix documents")
        
        # Show sample of what we're loading
        if docs:
            print(f"\n📝 Sample document:")
            sample_doc = docs[0]
            print(f"   Source: {sample_doc.metadata.get('source', 'Unknown')}")
            print(f"   Content preview: {sample_doc.page_content[:200]}...")
        
        # Upload to ChromaDB (reset=False to add to existing collection)
        print(f"\n🔄 Uploading TeamDynamix documents to ChromaDB...")
        doc_ids = utils.upload(
            general_collection, 
            teamdynamix_loader, 
            text_splitter, 
            reset=False,  # Don't reset, just add to existing collection
            batch_size=30
        )
        
        print(f"✅ Successfully uploaded {len(doc_ids)} document chunks")
        
        # Check new collection size
        new_collection_count = general_collection._collection.count()
        print(f"📊 New collection size: {new_collection_count} documents")
        print(f"📈 Added: {new_collection_count - collection_count} new chunks")
        
        # Test if TeamDynamix content is now retrievable
        print(f"\n🔍 Testing retrieval of TeamDynamix content...")
        test_queries = [
            "Microsoft 365 password",
            "Zoom desktop application", 
            "TeamDynamix"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            search_results = general_collection.similarity_search(query, k=5)
            
            teamdx_results = []
            for result in search_results:
                source = result.metadata.get('source', 'Unknown')
                if 'teamdynamix.com' in source:
                    teamdx_results.append(result)
            
            if teamdx_results:
                print(f"   ✅ Found {len(teamdx_results)} TeamDynamix results")
                for i, result in enumerate(teamdx_results[:2], 1):
                    print(f"      {i}. {result.metadata.get('source', 'Unknown')}")
            else:
                print(f"   ❌ No TeamDynamix results found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = ingest_teamdynamix_data()
    if success:
        print(f"\n🎉 TeamDynamix data ingestion completed successfully!")
    else:
        print(f"\n💥 TeamDynamix data ingestion failed!")
