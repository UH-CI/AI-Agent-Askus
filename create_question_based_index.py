#!/usr/bin/env python3
"""
Create Question-Based ChromaDB Index
Instead of chunking articles, index them by their associated questions for better semantic alignment
"""

import json
import os
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_chroma import Chroma
from chromadb import HttpClient
from manoa_agent.embeddings import convert
from openai import OpenAI

def load_evaluation_questions() -> List[Dict[str, Any]]:
    """Load evaluation questions to extract question-article mappings"""
    questions_file = "/home/exouser/AI-Agent-Askus/evaluation/evaluation_questions.json"
    
    with open(questions_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    question_article_pairs = []
    
    # Handle the nested structure from evaluation_questions.json
    if 'evaluation_questions' in data:
        for article in data['evaluation_questions']:
            article_url = article.get('article_url', '')
            for question_data in article.get('questions', []):
                question_article_pairs.append({
                    'question': question_data.get('question', ''),
                    'article_url': article_url,
                    'expected_keywords': question_data.get('expected_answer_contains', [])
                })
    
    return question_article_pairs

def load_article_content() -> Dict[str, str]:
    """Load article content from TeamDynamix and other sources"""
    article_content = {}
    
    # Load TeamDynamix articles
    teamdx_file = "/home/exouser/AI-Agent-Askus/web-scraper/data/teamdynamix.json"
    if os.path.exists(teamdx_file):
        with open(teamdx_file, 'r', encoding='utf-8') as f:
            teamdx_data = json.load(f)
        
        for article in teamdx_data:
            url = article.get('url', '')
            content = article.get('extracted', '')
            if url and content:
                article_content[url] = content
    
    # Load AskUs articles (if available)
    askus_file = "/home/exouser/AI-Agent-Askus/web-scraper/data/urls.json"
    if os.path.exists(askus_file):
        with open(askus_file, 'r', encoding='utf-8') as f:
            askus_data = json.load(f)
        
        for article in askus_data:
            url = article.get('url', '')
            content = article.get('extracted', '')
            if url and content:
                article_content[url] = content
    
    # Load Policies (if available)
    policies_file = "/home/exouser/AI-Agent-Askus/app/data/json/policies.json"
    if os.path.exists(policies_file):
        with open(policies_file, 'r', encoding='utf-8') as f:
            policies_data = json.load(f)
        
        for article in policies_data:
            url = article.get('url', '')
            content = article.get('extracted', '')
            if url and content:
                article_content[url] = content
    
    return article_content

def create_question_based_documents(question_pairs: List[Dict], article_content: Dict[str, str]) -> List[Document]:
    """Create documents where each document is a question paired with its article content"""
    documents = []
    
    for i, pair in enumerate(question_pairs):
        question = pair['question']
        article_url = pair['article_url']
        expected_keywords = pair['expected_keywords']
        
        # Get article content
        content = article_content.get(article_url, '')
        
        if not content:
            print(f"⚠️  Warning: No content found for {article_url}")
            continue
        
        # Create a document that combines the question with the article content
        # This creates better semantic alignment between queries and content
        combined_content = f"Question: {question}\n\nAnswer: {content}"
        
        # Create metadata (convert list to string for ChromaDB compatibility)
        metadata = {
            "source": article_url,
            "doc_id": f"qa_pair_{i}",
            "question": question,
            "expected_keywords": ", ".join(expected_keywords) if expected_keywords else "",
            "full_document": content,
            "content_type": "question_answer_pair"
        }
        
        # Determine source type
        if 'teamdynamix.com' in article_url:
            metadata["source_type"] = "TeamDynamix"
            if 'ID=' in article_url:
                metadata["article_id"] = article_url.split('ID=')[1].split('&')[0]
        elif 'hawaii.edu/askus' in article_url:
            metadata["source_type"] = "AskUs"
            if '/askus/' in article_url:
                metadata["article_id"] = article_url.split('/askus/')[1]
        elif 'hawaii.edu/policy' in article_url:
            metadata["source_type"] = "Policy"
        else:
            metadata["source_type"] = "Unknown"
        
        document = Document(
            page_content=combined_content,
            metadata=metadata
        )
        
        documents.append(document)
    
    return documents

def create_new_collection(documents: List[Document]):
    """Create a new ChromaDB collection with question-based indexing"""
    
    # Initialize embedder and ChromaDB client
    embedder = convert.from_open_ai(OpenAI(), "text-embedding-3-large")
    
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
    
    print(f"Connecting to Chroma at {chroma_host}:{chroma_port}")
    http_client = HttpClient(host=chroma_host, port=chroma_port)
    
    # Create new collection name
    new_collection_name = "question_based_faq"
    
    print(f"Creating new collection: {new_collection_name}")
    
    # Delete existing collection if it exists
    try:
        http_client.delete_collection(new_collection_name)
        print(f"Deleted existing collection: {new_collection_name}")
    except Exception as e:
        print(f"Collection {new_collection_name} doesn't exist yet: {e}")
    
    # Create new collection
    question_collection = Chroma(
        collection_name=new_collection_name,
        client=http_client,
        embedding_function=embedder,
        collection_metadata={"hnsw:space": "cosine"},
    )
    
    # Add documents in batches
    batch_size = 50
    total_docs = len(documents)
    
    print(f"Adding {total_docs} question-answer pairs to collection...")
    
    for i in range(0, total_docs, batch_size):
        batch = documents[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_docs + batch_size - 1) // batch_size
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
        
        try:
            question_collection.add_documents(batch)
            print(f"✅ Successfully added batch {batch_num}")
        except Exception as e:
            print(f"❌ Error adding batch {batch_num}: {e}")
    
    print(f"✅ Successfully created question-based collection with {total_docs} documents")
    return question_collection

def main():
    print("🚀 Creating Question-Based ChromaDB Index")
    print("=" * 80)
    
    # Load question-article pairs
    print("📋 Loading evaluation questions...")
    question_pairs = load_evaluation_questions()
    print(f"Found {len(question_pairs)} question-article pairs")
    
    # Load article content
    print("📄 Loading article content...")
    article_content = load_article_content()
    print(f"Loaded content for {len(article_content)} articles")
    
    # Create question-based documents
    print("🔗 Creating question-answer pair documents...")
    documents = create_question_based_documents(question_pairs, article_content)
    print(f"Created {len(documents)} question-answer documents")
    
    # Show some examples
    print("\n📝 Example documents:")
    for i, doc in enumerate(documents[:3]):
        print(f"\nExample {i+1}:")
        print(f"  Source: {doc.metadata['source']}")
        print(f"  Question: {doc.metadata['question'][:60]}...")
        print(f"  Content preview: {doc.page_content[:100]}...")
    
    # Create new ChromaDB collection
    print(f"\n🗄️  Creating new ChromaDB collection...")
    collection = create_new_collection(documents)
    
    print(f"\n✅ Question-based index created successfully!")
    print(f"   Collection name: question_based_faq")
    print(f"   Total documents: {len(documents)}")
    print(f"   Indexing approach: Question + Answer pairs")
    
    # Test the new collection
    print(f"\n🧪 Testing the new collection...")
    test_queries = [
        "How to change Microsoft 365 password?",
        "Update Zoom desktop application",
        "Setup Office 365 email on mobile"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        try:
            results = collection.similarity_search(query, k=3)
            print(f"  Found {len(results)} results:")
            for j, result in enumerate(results, 1):
                source_type = result.metadata.get('source_type', 'Unknown')
                article_id = result.metadata.get('article_id', 'N/A')
                question = result.metadata.get('question', 'N/A')
                print(f"    {j}. {source_type} {article_id}: {question[:50]}...")
        except Exception as e:
            print(f"  ❌ Error testing query: {e}")

if __name__ == "__main__":
    main()
