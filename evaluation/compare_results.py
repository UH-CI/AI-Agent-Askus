#!/usr/bin/env python3
"""
Re-run the failed questions and compare with original results
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
            
            if assistant_response:
                return {
                    "success": True,
                    "answer": assistant_response,
                    "response_time": response.elapsed.total_seconds(),
                    "sources": output.get('sources', [])
                }
            else:
                return {"success": False, "error": "No response content"}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def analyze_answer_quality(answer: str, expected_keywords: List[str]) -> Dict[str, Any]:
    """Analyze the quality of an answer"""
    answer_lower = answer.lower()
    
    # Check if it's the default "I don't know" response
    is_default_response = "i'm sorry i don't have the answer" in answer_lower
    
    # Check keyword coverage
    keywords_found = []
    keywords_missing = []
    
    for keyword in expected_keywords:
        if keyword.lower() in answer_lower:
            keywords_found.append(keyword)
        else:
            keywords_missing.append(keyword)
    
    keyword_coverage = len(keywords_found) / len(expected_keywords) if expected_keywords else 0
    
    return {
        "is_default_response": is_default_response,
        "keyword_coverage": keyword_coverage,
        "keywords_found": keywords_found,
        "keywords_missing": keywords_missing,
        "answer_length": len(answer),
        "has_specific_content": not is_default_response and len(answer) > 250
    }

def main():
    # Load original evaluation results to get the exact same questions that failed
    with open("/home/exouser/AI-Agent-Askus/evaluation/agent_evaluation_results.json", "r") as f:
        original_results = json.load(f)
    
    # Extract 5 questions that had 0% keyword coverage from original results
    failed_questions = []
    
    for article in original_results.get("article_evaluations", []):
        for question_result in article.get("question_results", []):
            if (question_result.get("evaluation", {}).get("keyword_coverage", 0) == 0.0 and 
                len(failed_questions) < 5):
                failed_questions.append({
                    "question": question_result["question"],
                    "expected_keywords": question_result["expected_answer_contains"],
                    "original_answer": question_result["api_response"]["answer"],
                    "original_sources": question_result["api_response"].get("sources", []),
                    "article_url": article["article_url"]
                })
    
    print("🔄 Re-running Failed Questions with Updated Settings")
    print("=" * 70)
    print("📊 Settings: score_threshold=0.4, k=16 (was similarity k=15)")
    print("=" * 70)
    
    # Wait for API to be ready
    time.sleep(5)
    
    comparison_results = []
    
    for i, test_case in enumerate(failed_questions, 1):
        print(f"\n📝 Question {i}/5:")
        print(f"🔗 Source: {test_case['article_url']}")
        print(f"❓ Question: {test_case['question'][:80]}...")
        print("-" * 50)
        
        # Get new result
        new_result = send_question_to_api(test_case["question"])
        
        if new_result.get("success"):
            new_analysis = analyze_answer_quality(new_result["answer"], test_case["expected_keywords"])
            original_analysis = analyze_answer_quality(test_case["original_answer"], test_case["expected_keywords"])
            
            # Compare results
            improvement_score = 0
            improvements = []
            regressions = []
            
            # Check for improvements
            if original_analysis["is_default_response"] and not new_analysis["is_default_response"]:
                improvement_score += 3
                improvements.append("✅ No longer default response")
            
            if new_analysis["keyword_coverage"] > original_analysis["keyword_coverage"]:
                improvement_score += 2
                improvements.append(f"✅ Keyword coverage: {original_analysis['keyword_coverage']:.1%} → {new_analysis['keyword_coverage']:.1%}")
            
            if new_analysis["has_specific_content"] and not original_analysis["has_specific_content"]:
                improvement_score += 1
                improvements.append("✅ Now has specific content")
            
            if len(new_result.get("sources", [])) > len(test_case["original_sources"]):
                improvements.append(f"✅ More sources: {len(test_case['original_sources'])} → {len(new_result.get('sources', []))}")
            
            # Check for regressions
            if not original_analysis["is_default_response"] and new_analysis["is_default_response"]:
                improvement_score -= 3
                regressions.append("❌ Now giving default response")
            
            if new_analysis["keyword_coverage"] < original_analysis["keyword_coverage"]:
                improvement_score -= 2
                regressions.append(f"❌ Keyword coverage decreased: {original_analysis['keyword_coverage']:.1%} → {new_analysis['keyword_coverage']:.1%}")
            
            # Determine overall status
            if improvement_score > 0:
                status = "🟢 IMPROVED"
            elif improvement_score < 0:
                status = "🔴 WORSE"
            else:
                status = "🟡 NO CHANGE"
            
            print(f"📊 {status} (Score: {improvement_score:+d})")
            
            if improvements:
                for imp in improvements:
                    print(f"  {imp}")
            
            if regressions:
                for reg in regressions:
                    print(f"  {reg}")
            
            if new_analysis["keywords_found"]:
                print(f"  🎯 Found keywords: {new_analysis['keywords_found']}")
            
            print(f"  🔗 Sources: {new_result.get('sources', [])}")
            print(f"  📝 Answer preview: {new_result['answer'][:100]}...")
            
            comparison_results.append({
                "question": test_case["question"],
                "article_url": test_case["article_url"],
                "expected_keywords": test_case["expected_keywords"],
                "original": {
                    "answer": test_case["original_answer"],
                    "sources": test_case["original_sources"],
                    "analysis": original_analysis
                },
                "new": {
                    "answer": new_result["answer"],
                    "sources": new_result.get("sources", []),
                    "analysis": new_analysis
                },
                "improvement_score": improvement_score,
                "improvements": improvements,
                "regressions": regressions,
                "status": status
            })
        else:
            print(f"❌ Failed to get new result: {new_result.get('error')}")
            comparison_results.append({
                "question": test_case["question"],
                "article_url": test_case["article_url"],
                "error": new_result.get("error"),
                "status": "🔴 ERROR"
            })
        
        time.sleep(1)  # Rate limiting
    
    # Overall summary
    print("\n" + "=" * 70)
    print("📊 OVERALL COMPARISON SUMMARY")
    print("=" * 70)
    
    improved = sum(1 for r in comparison_results if r.get("improvement_score", 0) > 0)
    worse = sum(1 for r in comparison_results if r.get("improvement_score", 0) < 0)
    no_change = sum(1 for r in comparison_results if r.get("improvement_score", 0) == 0)
    errors = sum(1 for r in comparison_results if "error" in r)
    
    total_improvement = sum(r.get("improvement_score", 0) for r in comparison_results)
    
    print(f"🟢 Improved: {improved}/5")
    print(f"🔴 Worse: {worse}/5") 
    print(f"🟡 No change: {no_change}/5")
    print(f"❌ Errors: {errors}/5")
    print(f"📈 Total improvement score: {total_improvement:+d}")
    
    # Detailed breakdown
    print(f"\n📋 Question-by-question results:")
    for i, result in enumerate(comparison_results, 1):
        status = result.get("status", "❌ ERROR")
        score = result.get("improvement_score", 0)
        print(f"  Q{i}: {status} ({score:+d}) - {result.get('article_url', 'Unknown')}")
    
    # Save detailed comparison
    output_data = {
        "comparison_metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "settings": {
                "old": "similarity search, k=15",
                "new": "similarity_score_threshold=0.4, k=16"
            }
        },
        "summary": {
            "improved": improved,
            "worse": worse,
            "no_change": no_change,
            "errors": errors,
            "total_improvement_score": total_improvement
        },
        "detailed_results": comparison_results
    }
    
    with open("/home/exouser/AI-Agent-Askus/evaluation/comparison_results.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Detailed comparison saved to: comparison_results.json")

if __name__ == "__main__":
    main()
