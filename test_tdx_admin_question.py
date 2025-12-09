#!/usr/bin/env python3
"""
Test specific TDX admin question to see what articles are retrieved
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
    question = "What resource can new TDX admins use to understand the differences between TeamDynamix and other ITSM tools?"
    
    print(f"🔍 Testing TDX Admin Question")
    print("=" * 80)
    print(f"❓ Question: {question}")
    print("=" * 80)
    
    result = send_question_to_api(question)
    
    if result["success"]:
        print(f"✅ Query successful!")
        print(f"⏱️  Response time: {result['response_time']:.2f} seconds")
        
        answer = result['answer']
        is_sorry = "sorry" in answer.lower() and "don't have" in answer.lower()
        
        if is_sorry:
            print(f"❌ Sorry response:")
            print(f"   {answer}")
        else:
            print(f"✅ Real answer:")
            print(f"   {answer}")
        
        print(f"\n📚 SOURCES RETRIEVED:")
        sources = result.get('sources', [])
        
        if not sources:
            print("   ❌ No sources retrieved")
        else:
            teamdx_sources = []
            other_sources = []
            
            for i, source in enumerate(sources, 1):
                source_str = str(source)
                print(f"\n{i}. {source_str}")
                
                if 'teamdynamix.com' in source_str:
                    teamdx_sources.append(source)
                    # Extract article ID
                    if 'ID=' in source_str:
                        article_id = source_str.split('ID=')[1].split('&')[0]
                        print(f"   🎯 TeamDynamix Article ID: {article_id}")
                else:
                    other_sources.append(source)
                    print(f"   📄 Other source")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total sources: {len(sources)}")
        print(f"   TeamDynamix sources: {len(teamdx_sources)}")
        print(f"   Other sources: {len(other_sources)}")
        
        # Check if this should have found the ITSM crosswalk article
        if teamdx_sources:
            print(f"\n🎯 TEAMDYNAMIX ARTICLES FOUND:")
            for i, source in enumerate(teamdx_sources, 1):
                source_str = str(source)
                if 'ID=' in source_str:
                    article_id = source_str.split('ID=')[1].split('&')[0]
                    print(f"   {i}. Article ID {article_id}")
                    
                    # Check if this is the expected ITSM crosswalk article
                    if article_id == "156033":
                        print(f"      ✅ This should be the ITSM Tool Feature Crosswalk!")
                    else:
                        print(f"      ❓ Different article - checking relevance...")
        
        # Expected answer analysis
        expected_keywords = ["ITSM Tool Feature Crosswalk", "crosswalk", "other ITSM tools", "TDX admins"]
        found_keywords = []
        
        for keyword in expected_keywords:
            if keyword.lower() in answer.lower():
                found_keywords.append(keyword)
        
        print(f"\n🔍 KEYWORD ANALYSIS:")
        print(f"   Expected keywords: {expected_keywords}")
        print(f"   Found keywords: {found_keywords}")
        print(f"   Keyword coverage: {len(found_keywords)}/{len(expected_keywords)} ({len(found_keywords)/len(expected_keywords)*100:.1f}%)")
        
        if len(found_keywords) >= 2:
            print(f"   ✅ Good keyword coverage - likely relevant answer")
        else:
            print(f"   ⚠️  Low keyword coverage - may not be the expected answer")
            
    else:
        print(f"❌ Query failed: {result['error']}")

if __name__ == "__main__":
    main()
