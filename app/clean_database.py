#!/usr/bin/env python3
"""
Clean the vector database by removing Hawaii.edu frontend URLs
Keep only TeamDynamix and AskUs content
"""

import os
from chromadb import HttpClient
from dotenv import load_dotenv

load_dotenv(override=True)

def clean_database():
    """Remove Hawaii.edu frontend URLs from the vector database"""
    
    # Connect to ChromaDB
    http_client = HttpClient(host=os.getenv('CHROMA_HOST'), port=os.getenv('CHROMA_PORT'))
    
    try:
        collection = http_client.get_collection('general_faq')
        
        print("🔍 Analyzing current database content...")
        
        # Get all documents with metadata
        all_results = collection.get(include=['metadatas', 'ids'])
        
        # Categorize sources
        askus_ids = []
        teamdynamix_ids = []
        policies_ids = []
        frontend_ids = []
        
        for doc_id, meta in zip(all_results['ids'], all_results['metadatas']):
            source = meta.get('source', '')
            
            if '/askus/' in source:
                askus_ids.append(doc_id)
            elif 'teamdynamix' in source:
                teamdynamix_ids.append(doc_id)
            elif 'policies.json' in source or 'policy' in source.lower():
                policies_ids.append(doc_id)
            elif 'hawaii.edu' in source:
                frontend_ids.append(doc_id)
            else:
                # Other sources - let's keep them for now
                pass
        
        print(f"📊 Current database breakdown:")
        print(f"  - AskUs articles: {len(askus_ids)}")
        print(f"  - TeamDynamix articles: {len(teamdynamix_ids)}")
        print(f"  - UH Policies: {len(policies_ids)}")
        print(f"  - Frontend URLs (to remove): {len(frontend_ids)}")
        print(f"  - Total documents: {len(all_results['ids'])}")
        
        if len(frontend_ids) == 0:
            print("✅ No frontend URLs found to remove!")
            return
        
        print(f"\n🗑️  Removing {len(frontend_ids)} frontend URL documents...")
        
        # Remove frontend URLs in batches (ChromaDB has limits)
        batch_size = 1000
        removed_count = 0
        
        for i in range(0, len(frontend_ids), batch_size):
            batch_ids = frontend_ids[i:i + batch_size]
            collection.delete(ids=batch_ids)
            removed_count += len(batch_ids)
            print(f"  Removed batch {i//batch_size + 1}: {removed_count}/{len(frontend_ids)} documents")
        
        print(f"\n✅ Successfully removed {removed_count} frontend URL documents!")
        
        # Verify the cleanup
        final_count = collection.count()
        print(f"📈 Final database size: {final_count} documents")
        print(f"📉 Removed: {len(all_results['ids']) - final_count} documents")
        
        # Show sample of remaining content
        sample_results = collection.get(limit=5, include=['documents', 'metadatas'])
        print(f"\n📋 Sample of remaining content:")
        for i, (doc, meta) in enumerate(zip(sample_results['documents'], sample_results['metadatas']), 1):
            source = meta.get('source', 'Unknown')
            print(f"  {i}. {source}")
            print(f"     {doc[:80]}...")
        
    except Exception as e:
        print(f"❌ Error cleaning database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧹 Starting database cleanup...")
    print("=" * 50)
    
    success = clean_database()
    
    if success:
        print("\n🎉 Database cleanup completed successfully!")
        print("The vector database now contains only:")
        print("  - TeamDynamix knowledge base articles")
        print("  - UH AskUs FAQ articles") 
        print("  - UH System policies")
    else:
        print("\n❌ Database cleanup failed!")
