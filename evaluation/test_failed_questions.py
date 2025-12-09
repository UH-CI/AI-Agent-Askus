#!/usr/bin/env python3
"""
Test 5 failed questions with the updated retrieval settings
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
        print(f"🔄 Testing: {question[:80]}...")
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            result = response.json()
            output = result.get('output', {})
            message = output.get('message', {})
            assistant_response = message.get('content', '')
            
            if assistant_response:
                print(f"✅ Response ({len(assistant_response)} chars): {assistant_response[:100]}...")
                return {
                    "success": True,
                    "answer": assistant_response,
                    "response_time": response.elapsed.total_seconds(),
                    "sources": output.get('sources', [])
                }
            else:
                print(f"❌ No response content")
                return {"success": False, "error": "No response content"}
        else:
            print(f"❌ API error: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}

def main():
    # 5 failed questions from the evaluation results
    failed_questions = [
        {
            "question": "What steps should you follow to update your Zoom Desktop Application to the latest version?",
            "expected_keywords": ["click profile", "check for updates", "download latest version"],
            "source_article": "Zoom Desktop Application update"
        },
        {
            "question": "What should you do if you encounter issues after attempting to update the Zoom Desktop Application?",
            "expected_keywords": ["restart your computer"],
            "source_article": "Zoom Desktop Application troubleshooting"
        },
        {
            "question": "What are the steps to change your Microsoft 365 password using the web interface?",
            "expected_keywords": ["Sign in to office.com/signin", "Settings > Password", "Enter old password", "Create a new password", "Select Submit"],
            "source_article": "Microsoft 365 password change"
        },
        {
            "question": "How can you forward a spam email as an attachment using Microsoft Outlook on Windows?",
            "expected_keywords": ["highlight message", "Ctrl + Alt + F", "Forward as attachment"],
            "source_article": "Spam email reporting"
        },
        {
            "question": "What are the steps to connect to the organization's network using the Cisco AnyConnect VPN client?",
            "expected_keywords": ["Launch Cisco AnyConnect", "evpn2.sample.com", "Connect", "Login with UserID"],
            "source_article": "VPN connection setup"
        }
    ]
    
    print("🚀 Testing 5 Failed Questions with Updated Retrieval Settings")
    print("=" * 70)
    print("📊 New Settings: score_threshold=0.4, k=16")
    print("=" * 70)
    
    # Wait for container to be ready
    print("⏳ Waiting for API to be ready...")
    time.sleep(10)
    
    results = []
    
    for i, test_case in enumerate(failed_questions, 1):
        print(f"\n📝 Question {i}/5: {test_case['source_article']}")
        print("-" * 50)
        
        result = send_question_to_api(test_case["question"])
        
        if result.get("success"):
            # Check keyword coverage
            answer = result["answer"].lower()
            keywords_found = []
            keywords_missing = []
            
            for keyword in test_case["expected_keywords"]:
                if keyword.lower() in answer:
                    keywords_found.append(keyword)
                else:
                    keywords_missing.append(keyword)
            
            keyword_coverage = len(keywords_found) / len(test_case["expected_keywords"]) if test_case["expected_keywords"] else 0
            
            print(f"📊 Keyword Coverage: {keyword_coverage:.1%}")
            if keywords_found:
                print(f"✅ Found: {keywords_found}")
            if keywords_missing:
                print(f"❌ Missing: {keywords_missing}")
            print(f"🔗 Sources: {result.get('sources', [])}")
            
            results.append({
                "question": test_case["question"],
                "source_article": test_case["source_article"],
                "success": True,
                "answer": result["answer"],
                "keyword_coverage": keyword_coverage,
                "keywords_found": keywords_found,
                "keywords_missing": keywords_missing,
                "sources": result.get("sources", []),
                "response_time": result.get("response_time", 0)
            })
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            results.append({
                "question": test_case["question"],
                "source_article": test_case["source_article"],
                "success": False,
                "error": result.get("error", "Unknown error")
            })
        
        time.sleep(1)  # Rate limiting
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY RESULTS")
    print("=" * 70)
    
    successful = sum(1 for r in results if r.get("success"))
    total_coverage = sum(r.get("keyword_coverage", 0) for r in results if r.get("success"))
    avg_coverage = total_coverage / successful if successful > 0 else 0
    
    print(f"✅ Successful responses: {successful}/5")
    print(f"📈 Average keyword coverage: {avg_coverage:.1%}")
    
    for i, result in enumerate(results, 1):
        if result.get("success"):
            coverage = result.get("keyword_coverage", 0)
            status = "🟢" if coverage > 0.5 else "🟡" if coverage > 0 else "🔴"
            print(f"{status} Q{i}: {coverage:.1%} - {result['source_article']}")
        else:
            print(f"🔴 Q{i}: FAILED - {result['source_article']}")
    
    # Save results
    with open("/home/exouser/AI-Agent-Askus/evaluation/failed_questions_retest.json", "w") as f:
        json.dump({
            "test_settings": {
                "score_threshold": 0.4,
                "k": 16,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "results": results,
            "summary": {
                "successful_responses": successful,
                "average_keyword_coverage": avg_coverage
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: failed_questions_retest.json")

if __name__ == "__main__":
    main()
