#!/usr/bin/env python3
"""
Test specific TeamDynamix queries that should match available content
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

def main():
    # Test queries that should match actual TeamDynamix content
    teamdynamix_queries = [
        "How do I install Spirion software?",
        "How to connect to eduroam on macOS?",
        "How to setup eduroam on Android?",
        "How to create a Google Group and Calendar?",
        "How to enable Google Consumer Apps?",
        "How to add Hawaiian diacritics in Google Docs?",
        "How to connect to UH VPN using SoftEther?",
        "How to request a first.last email alias?",
        "How to reset my UH password?",
        "How to setup Duo MFA on smartphone?",
        "How to create a change request in TeamDynamix?",
        "What are UH password requirements?",
        "How to enroll in Ohana Online Services?"
    ]
    
    for query in teamdynamix_queries:
        print(f"\n🔍 Testing query: {query}")
        print("=" * 80)
        
        result = send_question_to_api(query)
        
        if result["success"]:
            print(f"✅ Query successful!")
            print(f"⏱️  Response time: {result['response_time']:.2f} seconds")
            
            # Check if it's a "sorry" response
            answer = result['answer']
            is_sorry = "sorry" in answer.lower() and "don't have" in answer.lower()
            
            if is_sorry:
                print(f"❌ Sorry response: {answer[:100]}...")
            else:
                print(f"✅ Real answer: {answer[:200]}...")
            
            sources = result.get('sources', [])
            teamdx_sources = []
            other_sources = []
            
            for source in sources:
                if isinstance(source, str):
                    if 'teamdynamix.com' in source:
                        teamdx_sources.append(source)
                    else:
                        other_sources.append(source)
            
            print(f"📊 Sources: {len(teamdx_sources)} TeamDynamix, {len(other_sources)} Other")
            
            if teamdx_sources:
                print(f"🎯 TeamDynamix sources:")
                for i, source in enumerate(teamdx_sources, 1):
                    # Extract article ID
                    if 'ID=' in source:
                        article_id = source.split('ID=')[1].split('&')[0]
                        print(f"   {i}. Article ID {article_id}")
                    else:
                        print(f"   {i}. {source}")
            
            # Show success/failure summary
            if teamdx_sources and not is_sorry:
                print(f"🎉 SUCCESS: TeamDynamix content retrieved and used!")
            elif teamdx_sources and is_sorry:
                print(f"⚠️  PARTIAL: TeamDynamix retrieved but 'sorry' response")
            else:
                print(f"❌ FAILED: No TeamDynamix sources retrieved")
                
        else:
            print(f"❌ Query failed: {result['error']}")
        
        print("\n" + "🔄" * 40)

if __name__ == "__main__":
    main()
