#!/usr/bin/env python3
"""
Check what TeamDynamix articles are actually stored in ChromaDB
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

def check_chromadb_content():
    # Initialize ChromaDB connection
    embedder = OpenAIEmbeddingAdapter(OpenAI(), "text-embedding-3-large")
    http_client = HttpClient(host=os.getenv("CHROMA_HOST"), port=os.getenv("CHROMA_PORT"))
    
    general_collection = Chroma(
        collection_name="general_faq",
        client=http_client,
        embedding_function=embedder,
        collection_metadata={"hnsw:space": "cosine"},
    )
    
    print("🔍 Checking ChromaDB content...")
    print("=" * 80)
    
    # Get collection info
    try:
        collection_count = general_collection._collection.count()
        print(f"📊 Total documents in collection: {collection_count}")
        
        # Try to find TeamDynamix documents by filtering
        print(f"\n🔍 Searching for TeamDynamix documents by metadata...")
        
        # Use where clause to filter for TeamDynamix sources
        try:
            teamdx_results = general_collection._collection.get(
                where={"source": {"$regex": "teamdynamix.com"}},
                limit=100,
                include=['metadatas', 'documents']
            )
            print(f"📊 Found {len(teamdx_results['documents'])} TeamDynamix documents using regex filter")
        except Exception as e:
            print(f"❌ Regex filter failed: {e}")
            teamdx_results = {'documents': [], 'metadatas': []}
        
        # Also get a sample of all documents to see the distribution
        results = general_collection._collection.get(
            limit=1000,  # Get first 1000 documents
            include=['metadatas', 'documents']
        )
        
        teamdynamix_docs = []
        hawaii_askus_docs = []
        policy_docs = []
        other_docs = []
        
        print(f"\n📋 Analyzing first 1000 documents...")
        
        for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
            source = metadata.get('source', 'Unknown')
            
            if 'teamdynamix.com' in source:
                teamdynamix_docs.append((source, doc[:100] + "..."))
            elif 'hawaii.edu/askus' in source:
                hawaii_askus_docs.append((source, doc[:100] + "..."))
            elif 'hawaii.edu/policy' in source:
                policy_docs.append((source, doc[:100] + "..."))
            else:
                other_docs.append((source, doc[:100] + "..."))
        
        print(f"\n📊 DOCUMENT BREAKDOWN (first 1000):")
        print(f"   TeamDynamix articles: {len(teamdynamix_docs)}")
        print(f"   Hawaii.edu/askus: {len(hawaii_askus_docs)}")
        print(f"   Policy documents: {len(policy_docs)}")
        print(f"   Other sources: {len(other_docs)}")
        
        # Show TeamDynamix results from direct search
        if teamdx_results['documents']:
            print(f"\n🎯 TEAMDYNAMIX DOCUMENTS FOUND VIA DIRECT SEARCH:")
            for i, (doc, metadata) in enumerate(zip(teamdx_results['documents'][:10], teamdx_results['metadatas'][:10]), 1):
                source = metadata.get('source', 'Unknown')
                print(f"   {i}. {source}")
                print(f"      Content: {doc[:100]}...")
                print()
        
        # Show TeamDynamix examples
        if teamdynamix_docs:
            print(f"\n🎯 TEAMDYNAMIX ARTICLES FOUND:")
            for i, (source, content) in enumerate(teamdynamix_docs[:10], 1):
                print(f"   {i}. {source}")
                print(f"      Content: {content}")
                print()
        else:
            print(f"\n❌ NO TEAMDYNAMIX ARTICLES FOUND in first 1000 documents")
        
        # Search for specific TeamDynamix content
        print(f"\n🔍 SEARCHING FOR SPECIFIC TEAMDYNAMIX CONTENT...")
        
        # Search for Microsoft 365 password content
        search_queries = [
            "Microsoft 365 password",
            "office.com/signin",
            "Zoom desktop application",
            "TeamDynamix"
        ]
        
        for query in search_queries:
            print(f"\n🔍 Searching for: '{query}'")
            search_results = general_collection.similarity_search(query, k=5)
            
            teamdx_results = []
            other_results = []
            
            for result in search_results:
                source = result.metadata.get('source', 'Unknown')
                if 'teamdynamix.com' in source:
                    teamdx_results.append(result)
                else:
                    other_results.append(result)
            
            print(f"   TeamDynamix results: {len(teamdx_results)}")
            print(f"   Other results: {len(other_results)}")
            
            if teamdx_results:
                print(f"   📋 TeamDynamix matches:")
                for i, result in enumerate(teamdx_results, 1):
                    print(f"      {i}. {result.metadata.get('source', 'Unknown')}")
                    print(f"         Content: {result.page_content[:100]}...")
            else:
                print(f"   ❌ No TeamDynamix matches found")
                
            if other_results:
                print(f"   📋 Other matches:")
                for i, result in enumerate(other_results[:3], 1):
                    print(f"      {i}. {result.metadata.get('source', 'Unknown')}")
        
        # Check for specific article IDs we know exist
        print(f"\n🔍 CHECKING FOR SPECIFIC ARTICLE IDs...")
        specific_ids = ["3728", "3729", "3730", "3731", "3732", "20178", "20132", "20130"]
        
        for article_id in specific_ids:
            search_results = general_collection.similarity_search(f"ID={article_id}", k=10)
            found = False
            for result in search_results:
                source = result.metadata.get('source', '')
                if article_id in source:
                    print(f"   ✅ Found article ID {article_id}: {source}")
                    found = True
                    break
            if not found:
                print(f"   ❌ Article ID {article_id} not found")
                
    except Exception as e:
        print(f"❌ Error accessing ChromaDB: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_chromadb_content()
