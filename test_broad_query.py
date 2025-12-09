#!/usr/bin/env python3
"""
Test a broad query to see if we can get more sources
"""

import json
import requests
import time
from typing import List, Dict, Any

def send_question_to_api(question: str, api_url: str = "http://localhost:8001/askus/invoke", timeout: int = 30) -> Dict[str, Any]:
    """Send a question to the AI agent API and return the response"""
    
    payload = {
        "input": {
            "messages": [
                {
                    "type": "human",
                    "content": question
                }
            ],
            "retriever": "general"
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            result = response.json()
            output = result.get('output', {})
            message = output.get('message', {})
            assistant_response = message.get('content', '')
            sources = output.get('sources', [])
            
            return {
                "success": True,
                "answer": assistant_response,
                "response_time": response.elapsed.total_seconds(),
                "sources": sources,
                "raw_response": result
            }
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}

def test_question(question):
    print(f"\n🔍 Testing: {question}")
    print("-" * 80)
    
    result = send_question_to_api(question)
    
    if result["success"]:
        sources = result.get('sources', [])
        print(f"📊 Retrieved {len(sources)} sources")
        
        teamdx_sources = []
        askus_sources = []
        policy_sources = []
        other_sources = []
        
        for i, source in enumerate(sources, 1):
            source_str = str(source)
            print(f"   {i}. {source_str}")
            
            if 'teamdynamix.com' in source_str:
                teamdx_sources.append(source)
                if 'ID=' in source_str:
                    article_id = source_str.split('ID=')[1].split('&')[0]
                    print(f"      🎯 TeamDynamix Article ID: {article_id}")
            elif 'hawaii.edu/askus' in source_str:
                askus_sources.append(source)
                if '/askus/' in source_str:
                    askus_id = source_str.split('/askus/')[1]
                    print(f"      📄 AskUs Article ID: {askus_id}")
            elif 'hawaii.edu/policy' in source_str:
                policy_sources.append(source)
                print(f"      📋 Policy document")
            else:
                other_sources.append(source)
                print(f"      ❓ Other source")
        
        print(f"\n📈 Summary: {len(teamdx_sources)} TeamDynamix, {len(askus_sources)} AskUs, {len(policy_sources)} Policy, {len(other_sources)} Other")
        
        answer = result['answer']
        is_sorry = "sorry" in answer.lower() and "don't have" in answer.lower()
        print(f"💬 Response type: {'❌ Sorry' if is_sorry else '✅ Real answer'}")
        
        return len(sources)
    else:
        print(f"❌ Query failed: {result['error']}")
        return 0

def main():
    print("🔄 Testing Broad Queries to Maximize Source Retrieval")
    print("=" * 80)
    
    # Test broader questions that might hit multiple sources
    broad_questions = [
        "How do I access university services?",
        "What are the IT support options at UH?", 
        "How to manage my UH account and password?",
        "What email and communication tools are available?",
        "How to connect to university networks and VPN?",
        "What are the authentication and security requirements?",
        "How to use Google services at UH?",
        "What policies and procedures should I know about?"
    ]
    
    source_counts = []
    max_sources = 0
    best_query = ""
    
    for question in broad_questions:
        count = test_question(question)
        source_counts.append(count)
        
        if count > max_sources:
            max_sources = count
            best_query = question
        
        time.sleep(1)  # Brief pause between requests
    
    print(f"\n📊 BROAD QUERY SUMMARY")
    print("=" * 80)
    print(f"Average sources per query: {sum(source_counts)/len(source_counts):.1f}")
    print(f"Max sources retrieved: {max_sources}")
    print(f"Best performing query: {best_query}")
    print(f"Min sources retrieved: {min(source_counts)}")
    print(f"Source counts: {source_counts}")
    
    if max_sources >= 5:
        print("🎉 Excellent! Getting 5+ sources for broad queries")
    elif max_sources >= 4:
        print("✅ Good! Getting 4+ sources for broad queries")
    elif max_sources >= 3:
        print("📈 Decent! Getting 3+ sources for broad queries")
    else:
        print("⚠️ Limited source diversity - may need further optimization")

if __name__ == "__main__":
    main()
