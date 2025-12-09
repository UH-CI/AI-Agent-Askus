#!/usr/bin/env python3
"""
Test query to see what TeamDynamix articles are retrieved for PDF reader question
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
    # Try a few different questions to see what gets retrieved
    questions = [
        "How can you change the default PDF reader to Adobe Acrobat Reader DC on a Windows computer?",
        "How do I change my Microsoft 365 password?",
        "How to update Zoom desktop application?",
        "TeamDynamix knowledge base articles"
    ]
    
    for question in questions:
        print(f"\n🔍 Testing query: {question}")
        print("=" * 80)
        
        result = send_question_to_api(question)
        
        if result["success"]:
            print(f"✅ Query successful!")
            print(f"⏱️  Response time: {result['response_time']:.2f} seconds")
            print(f"📝 Answer: {result['answer'][:200]}...")
            print("\n" + "=" * 80)
            print("📚 SOURCES RETRIEVED:")
            
            sources = result.get('sources', [])
            teamdynamix_sources = []
            other_sources = []
            
            print(f"Raw sources type: {type(sources)}")
            print(f"Raw sources: {sources}")
            
            # Handle different source formats
            if isinstance(sources, list):
                for i, source in enumerate(sources, 1):
                    if isinstance(source, dict):
                        source_url = source.get('source', 'Unknown source')
                        content_preview = source.get('page_content', '')[:150] + "..."
                    elif isinstance(source, str):
                        source_url = source
                        content_preview = "No content preview available"
                    else:
                        source_url = str(source)
                        content_preview = "Unknown format"
                    
                    print(f"\n{i}. Source: {source_url}")
                    print(f"   Content: {content_preview}")
                    
                    if 'teamdynamix.com' in str(source_url):
                        teamdynamix_sources.append(source)
                    else:
                        other_sources.append(source)
            else:
                print(f"Unexpected sources format: {sources}")
            
            print("\n" + "=" * 80)
            print(f"📊 SUMMARY:")
            print(f"   Total sources: {len(sources)}")
            print(f"   TeamDynamix sources: {len(teamdynamix_sources)}")
            print(f"   Other sources: {len(other_sources)}")
            
            if teamdynamix_sources:
                print(f"\n🎯 TEAMDYNAMIX ARTICLES FOUND:")
                for i, source in enumerate(teamdynamix_sources, 1):
                    if isinstance(source, dict):
                        print(f"   {i}. {source.get('source', 'Unknown')}")
                    else:
                        print(f"   {i}. {source}")
            else:
                print(f"\n❌ No TeamDynamix articles were retrieved for this query")
                
        else:
            print(f"❌ Query failed: {result['error']}")
        
        print("\n" + "🔄" * 80)

if __name__ == "__main__":
    main()
