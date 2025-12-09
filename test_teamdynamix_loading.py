#!/usr/bin/env python3
"""
Test script to verify TeamDynamix knowledge base loading
"""

import json
import sys
import os

# Add the app src to Python path
sys.path.append('/home/exouser/AI-Agent-Askus/app/src')

from manoa_agent.loaders.json_loader import JSONFileLoader

def test_teamdynamix_loading():
    """Test loading TeamDynamix JSON file"""
    
    json_file = "/home/exouser/AI-Agent-Askus/app/data/json/teamdynamix.json"
    
    print("🔍 Testing TeamDynamix Knowledge Base Loading")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        return False
    
    # Check file size
    file_size = os.path.getsize(json_file)
    print(f"📁 File: {json_file}")
    print(f"📊 Size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    
    # Test JSON loading
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        print(f"✅ JSON loaded successfully")
        print(f"📄 Total articles: {len(data)}")
        
        # Show sample article
        if data:
            sample = data[0]
            print(f"\n📋 Sample article:")
            print(f"   URL: {sample['url']}")
            print(f"   Content preview: {sample['extracted'][:100]}...")
        
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return False
    
    # Test JSONFileLoader
    try:
        print(f"\n🔧 Testing JSONFileLoader...")
        loader = JSONFileLoader(json_file)
        documents = loader.load()
        
        print(f"✅ JSONFileLoader created {len(documents)} documents")
        
        if documents:
            sample_doc = documents[0]
            print(f"📄 Sample document:")
            print(f"   Source: {sample_doc.metadata.get('source', 'N/A')}")
            print(f"   Content preview: {sample_doc.page_content[:100]}...")
            print(f"   Metadata keys: {list(sample_doc.metadata.keys())}")
        
    except Exception as e:
        print(f"❌ Error with JSONFileLoader: {e}")
        return False
    
    print(f"\n✅ All tests passed! TeamDynamix data is ready for loading.")
    return True

if __name__ == "__main__":
    success = test_teamdynamix_loading()
    sys.exit(0 if success else 1)
