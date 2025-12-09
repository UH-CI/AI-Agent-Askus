#!/usr/bin/env python3
"""
Test the specific Zoom question to see what sources are retrieved
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
    question = "What steps should you follow to update your Zoom Desktop Application to the latest version?"
    
    print(f"🔍 Testing Zoom Update Question")
    print("=" * 80)
    print(f"❓ Question: {question}")
    print("=" * 80)
    
    result = send_question_to_api(question)
    
    if result["success"]:
        print(f"✅ Query successful!")
        print(f"⏱️  Response time: {result['response_time']:.2f} seconds")
        
        answer = result['answer']
        is_sorry = "sorry" in answer.lower() and "don't have" in answer.lower()
        
        print(f"\n💬 RESPONSE:")
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
            askus_sources = []
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
                        
                        # Check if this matches expected articles
                        if article_id in ["20169", "20151"]:
                            print(f"   ✅ This matches the expected article from the failed test!")
                        else:
                            print(f"   ❓ Different article than expected")
                            
                elif 'hawaii.edu/askus' in source_str:
                    askus_sources.append(source)
                    # Extract askus ID
                    if '/askus/' in source_str:
                        askus_id = source_str.split('/askus/')[1]
                        print(f"   📄 AskUs Article ID: {askus_id}")
                        
                        if askus_id == "1737":
                            print(f"   ✅ This matches the expected AskUs article from the failed test!")
                else:
                    other_sources.append(source)
                    print(f"   📄 Other source")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total sources: {len(sources)}")
        print(f"   TeamDynamix sources: {len(teamdx_sources)}")
        print(f"   AskUs sources: {len(askus_sources)}")
        print(f"   Other sources: {len(other_sources)}")
        
        # Compare with the failed test results
        print(f"\n🔍 COMPARISON WITH FAILED TEST:")
        expected_sources = [
            "https://solutions.teamdynamix.com/TDClient/277/Portal/KB/ArticleDet?ID=20169",
            "https://www.hawaii.edu/askus/1737"
        ]
        
        current_sources = [str(s) for s in sources]
        
        print(f"   Expected sources from failed test:")
        for i, exp_source in enumerate(expected_sources, 1):
            print(f"      {i}. {exp_source}")
        
        print(f"   Current sources:")
        for i, curr_source in enumerate(current_sources, 1):
            print(f"      {i}. {curr_source}")
        
        # Check for matches
        matches = []
        for exp_source in expected_sources:
            for curr_source in current_sources:
                if exp_source == curr_source:
                    matches.append(exp_source)
        
        print(f"\n📈 MATCHING ANALYSIS:")
        print(f"   Matching sources: {len(matches)}/{len(expected_sources)}")
        for match in matches:
            print(f"   ✅ {match}")
        
        if len(matches) == len(expected_sources):
            print(f"   🎉 Perfect match with failed test sources!")
        elif len(matches) > 0:
            print(f"   📈 Partial match with failed test sources")
        else:
            print(f"   ❌ No matching sources with failed test")
            
        # Expected keywords analysis
        expected_keywords = ["click profile", "check for updates", "download latest version"]
        found_keywords = []
        
        for keyword in expected_keywords:
            if keyword.lower() in answer.lower():
                found_keywords.append(keyword)
        
        print(f"\n🔍 KEYWORD ANALYSIS:")
        print(f"   Expected keywords: {expected_keywords}")
        print(f"   Found keywords: {found_keywords}")
        print(f"   Keyword coverage: {len(found_keywords)}/{len(expected_keywords)} ({len(found_keywords)/len(expected_keywords)*100:.1f}%)")
        
        if len(found_keywords) >= 2:
            print(f"   ✅ Good keyword coverage")
        elif len(found_keywords) >= 1:
            print(f"   📈 Some keyword coverage")
        else:
            print(f"   ❌ No keyword coverage - likely not the right content")
            
    else:
        print(f"❌ Query failed: {result['error']}")

if __name__ == "__main__":
    main()
