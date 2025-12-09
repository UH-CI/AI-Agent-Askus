#!/usr/bin/env python3
"""
Check all unique sources in ChromaDB collection
"""

import os
from chromadb import HttpClient
from dotenv import load_dotenv
from langchain_chroma import Chroma
from openai import OpenAI
import sys
sys.path.append('/home/exouser/AI-Agent-Askus/app/src')

from manoa_agent.embeddings.convert import OpenAIEmbeddingAdapter

load_dotenv(override=True)

def check_all_sources():
    # Initialize ChromaDB connection
    embedder = OpenAIEmbeddingAdapter(OpenAI(), "text-embedding-3-large")
    http_client = HttpClient(host=os.getenv("CHROMA_HOST"), port=os.getenv("CHROMA_PORT"))
    
    general_collection = Chroma(
        collection_name="general_faq",
        client=http_client,
        embedding_function=embedder,
        collection_metadata={"hnsw:space": "cosine"},
    )
    
    print("🔍 Checking all sources in ChromaDB...")
    print("=" * 80)
    
    try:
        collection_count = general_collection._collection.count()
        print(f"📊 Total documents in collection: {collection_count}")
        
        # Get all documents in batches to find unique sources
        batch_size = 5000
        all_sources = set()
        teamdynamix_sources = set()
        askus_sources = set()
        policy_sources = set()
        other_sources = set()
        
        print(f"\n🔍 Scanning all {collection_count} documents for sources...")
        
        for offset in range(0, collection_count, batch_size):
            print(f"   Processing batch {offset//batch_size + 1}/{(collection_count//batch_size) + 1}...")
            
            # Get batch of documents
            results = general_collection._collection.get(
                limit=batch_size,
                offset=offset,
                include=['metadatas']
            )
            
            for metadata in results['metadatas']:
                source = metadata.get('source', 'Unknown')
                all_sources.add(source)
                
                if 'teamdynamix.com' in source:
                    teamdynamix_sources.add(source)
                elif 'hawaii.edu/askus' in source:
                    askus_sources.add(source)
                elif 'hawaii.edu/policy' in source:
                    policy_sources.add(source)
                else:
                    other_sources.add(source)
        
        print(f"\n📊 SOURCE ANALYSIS:")
        print(f"   Total unique sources: {len(all_sources)}")
        print(f"   TeamDynamix sources: {len(teamdynamix_sources)}")
        print(f"   Hawaii.edu/askus sources: {len(askus_sources)}")
        print(f"   Policy sources: {len(policy_sources)}")
        print(f"   Other sources: {len(other_sources)}")
        
        # Show TeamDynamix sources if any
        if teamdynamix_sources:
            print(f"\n🎯 TEAMDYNAMIX SOURCES FOUND:")
            for i, source in enumerate(sorted(teamdynamix_sources)[:20], 1):
                print(f"   {i}. {source}")
            if len(teamdynamix_sources) > 20:
                print(f"   ... and {len(teamdynamix_sources) - 20} more")
        else:
            print(f"\n❌ NO TEAMDYNAMIX SOURCES FOUND!")
            
        # Show sample of other sources
        print(f"\n📋 SAMPLE OF OTHER SOURCES:")
        print(f"   AskUs sources (first 10):")
        for i, source in enumerate(sorted(askus_sources)[:10], 1):
            print(f"      {i}. {source}")
            
        print(f"   Policy sources (first 10):")
        for i, source in enumerate(sorted(policy_sources)[:10], 1):
            print(f"      {i}. {source}")
            
        print(f"   Other sources (first 10):")
        for i, source in enumerate(sorted(other_sources)[:10], 1):
            print(f"      {i}. {source}")
            
    except Exception as e:
        print(f"❌ Error accessing ChromaDB: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_all_sources()
