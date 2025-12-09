#!/usr/bin/env python3
"""
Test if we're now getting multiple sources after configuration change
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
    print("-" * 60)
    
    result = send_question_to_api(question)
    
    if result["success"]:
        sources = result.get('sources', [])
        print(f"📊 Retrieved {len(sources)} sources")
        
        teamdx_sources = []
        other_sources = []
        
        for i, source in enumerate(sources, 1):
            source_str = str(source)
            print(f"   {i}. {source_str}")
            
            if 'teamdynamix.com' in source_str:
                teamdx_sources.append(source)
                if 'ID=' in source_str:
                    article_id = source_str.split('ID=')[1].split('&')[0]
                    print(f"      🎯 TeamDynamix Article ID: {article_id}")
            else:
                other_sources.append(source)
                print(f"      📄 Other source")
        
        print(f"📈 Summary: {len(teamdx_sources)} TeamDynamix, {len(other_sources)} Other")
        
        answer = result['answer']
        is_sorry = "sorry" in answer.lower() and "don't have" in answer.lower()
        print(f"💬 Response type: {'❌ Sorry' if is_sorry else '✅ Real answer'}")
        
        return len(sources)
    else:
        print(f"❌ Query failed: {result['error']}")
        return 0

def main():
    print("🔄 Testing Multiple Source Retrieval After Configuration Change")
    print("=" * 80)
    
    # Test various questions to see source counts
    test_questions = [
        "How to reset UH password?",
        "How to setup Duo MFA?", 
        "How to connect to VPN?",
        "TeamDynamix change request",
        "Microsoft 365 password change",
        "What are UH policies?",
        "How to use Google Apps?",
        "What is eduroam?"
    ]
    
    source_counts = []
    
    for question in test_questions:
        count = test_question(question)
        source_counts.append(count)
        time.sleep(1)  # Brief pause between requests
    
    print(f"\n📊 OVERALL SUMMARY")
    print("=" * 60)
    print(f"Average sources per query: {sum(source_counts)/len(source_counts):.1f}")
    print(f"Max sources retrieved: {max(source_counts)}")
    print(f"Min sources retrieved: {min(source_counts)}")
    print(f"Source counts: {source_counts}")
    
    if max(source_counts) >= 3:
        print("✅ Configuration change successful - getting multiple sources!")
    elif max(source_counts) >= 2:
        print("📈 Partial success - getting more sources than before")
    else:
        print("❌ Still only getting 1 source - configuration may not have taken effect")

if __name__ == "__main__":
    main()
