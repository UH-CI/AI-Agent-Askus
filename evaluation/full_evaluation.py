#!/usr/bin/env python3
"""
Complete evaluation of the AI agent on all generated questions
"""

import json
import requests
import time
from typing import List, Dict, Any
import os

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
    
    # Determine answer quality
    if is_default_response:
        quality = "poor"
    elif keyword_coverage >= 0.7:
        quality = "excellent"
    elif keyword_coverage >= 0.4:
        quality = "good"
    elif keyword_coverage > 0:
        quality = "fair"
    else:
        quality = "poor"
    
    return {
        "is_default_response": is_default_response,
        "keyword_coverage": keyword_coverage,
        "keywords_found": keywords_found,
        "keywords_missing": keywords_missing,
        "answer_length": len(answer),
        "quality": quality,
        "has_specific_content": not is_default_response and len(answer) > 250
    }

def main():
    """Run complete evaluation on all generated questions"""
    
    print("🚀 Starting Complete AI Agent Evaluation")
    print("=" * 60)
    
    # Load generated questions
    questions_file = "/home/exouser/AI-Agent-Askus/evaluation/evaluation_questions.json"
    
    if not os.path.exists(questions_file):
        print(f"❌ Questions file not found: {questions_file}")
        return
    
    with open(questions_file, "r") as f:
        questions_data = json.load(f)
    
    # Extract the evaluation questions array
    articles_data = questions_data.get("evaluation_questions", [])
    
    print(f"📊 Loaded {len(articles_data)} articles with questions")
    
    # Count total questions
    total_questions = sum(len(article.get("questions", [])) for article in articles_data)
    print(f"📝 Total questions to evaluate: {total_questions}")
    
    # Wait for API to be ready
    print("⏳ Waiting for API to be ready...")
    time.sleep(5)
    
    # Run evaluation
    results = {
        "evaluation_metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_articles": len(articles_data),
            "total_questions": total_questions,
            "settings": {
                "retrieval_method": "similarity_score_threshold",
                "score_threshold": 0.4,
                "k": 16
            }
        },
        "article_evaluations": [],
        "summary_stats": {}
    }
    
    question_count = 0
    successful_responses = 0
    quality_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
    total_keyword_coverage = 0
    source_types = {"teamdynamix": 0, "askus": 0, "hawaii_edu": 0, "other": 0}
    
    for article_idx, article in enumerate(articles_data, 1):
        print(f"\n📄 Article {article_idx}/{len(articles_data)}: {article['article_url']}")
        print("-" * 50)
        
        article_result = {
            "article_url": article["article_url"],
            "article_content_preview": article.get("content_preview", "")[:200] + "...",
            "question_results": []
        }
        
        for q_idx, question_data in enumerate(article.get("questions", []), 1):
            question_count += 1
            question = question_data["question"]
            expected_keywords = question_data["expected_answer_contains"]
            
            print(f"  Q{q_idx}: {question[:60]}...")
            
            # Send question to API
            api_response = send_question_to_api(question)
            
            if api_response.get("success"):
                successful_responses += 1
                
                # Analyze answer quality
                analysis = analyze_answer_quality(api_response["answer"], expected_keywords)
                quality_distribution[analysis["quality"]] += 1
                total_keyword_coverage += analysis["keyword_coverage"]
                
                # Categorize sources
                for source in api_response.get("sources", []):
                    if "teamdynamix" in source:
                        source_types["teamdynamix"] += 1
                    elif "askus" in source:
                        source_types["askus"] += 1
                    elif "hawaii.edu" in source:
                        source_types["hawaii_edu"] += 1
                    else:
                        source_types["other"] += 1
                
                # Status indicator
                if analysis["quality"] == "excellent":
                    status = "🟢"
                elif analysis["quality"] == "good":
                    status = "🟡"
                elif analysis["quality"] == "fair":
                    status = "🟠"
                else:
                    status = "🔴"
                
                print(f"    {status} {analysis['quality'].upper()} - Coverage: {analysis['keyword_coverage']:.1%}")
                
                question_result = {
                    "question": question,
                    "expected_answer_contains": expected_keywords,
                    "api_response": api_response,
                    "evaluation": analysis
                }
            else:
                print(f"    ❌ FAILED - {api_response.get('error', 'Unknown error')}")
                question_result = {
                    "question": question,
                    "expected_answer_contains": expected_keywords,
                    "api_response": api_response,
                    "evaluation": {"quality": "failed", "error": True}
                }
                quality_distribution["poor"] += 1
            
            article_result["question_results"].append(question_result)
            
            # Rate limiting
            time.sleep(0.5)
        
        results["article_evaluations"].append(article_result)
        
        # Progress update
        if article_idx % 5 == 0:
            print(f"\n📈 Progress: {article_idx}/{len(articles_data)} articles, {question_count} questions processed")
    
    # Calculate summary statistics
    avg_keyword_coverage = total_keyword_coverage / successful_responses if successful_responses > 0 else 0
    success_rate = successful_responses / total_questions if total_questions > 0 else 0
    
    results["summary_stats"] = {
        "total_questions": total_questions,
        "successful_responses": successful_responses,
        "success_rate": success_rate,
        "average_keyword_coverage": avg_keyword_coverage,
        "quality_distribution": quality_distribution,
        "source_types": source_types
    }
    
    # Display summary
    print("\n" + "=" * 60)
    print("📊 EVALUATION SUMMARY")
    print("=" * 60)
    
    print(f"✅ Success Rate: {success_rate:.1%} ({successful_responses}/{total_questions})")
    print(f"📈 Average Keyword Coverage: {avg_keyword_coverage:.1%}")
    
    print(f"\n🎯 Quality Distribution:")
    for quality, count in quality_distribution.items():
        percentage = count / total_questions * 100 if total_questions > 0 else 0
        print(f"  {quality.capitalize()}: {count} ({percentage:.1f}%)")
    
    print(f"\n🔗 Source Types Used:")
    total_sources = sum(source_types.values())
    for source_type, count in source_types.items():
        percentage = count / total_sources * 100 if total_sources > 0 else 0
        print(f"  {source_type.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    # Save results
    output_file = "/home/exouser/AI-Agent-Askus/evaluation/complete_evaluation_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Complete results saved to: {output_file}")
    
    # Performance assessment
    print(f"\n🎯 PERFORMANCE ASSESSMENT:")
    if success_rate >= 0.9 and avg_keyword_coverage >= 0.7:
        print("🟢 EXCELLENT - Agent performing very well")
    elif success_rate >= 0.8 and avg_keyword_coverage >= 0.5:
        print("🟡 GOOD - Agent performing adequately")
    elif success_rate >= 0.6 and avg_keyword_coverage >= 0.3:
        print("🟠 FAIR - Agent needs improvement")
    else:
        print("🔴 POOR - Agent requires significant improvement")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if quality_distribution["poor"] > total_questions * 0.5:
        print("  - Consider lowering retrieval threshold further")
        print("  - Review question phrasing vs. content alignment")
    if source_types["teamdynamix"] < source_types["askus"]:
        print("  - TeamDynamix content may need better indexing")
    if avg_keyword_coverage < 0.5:
        print("  - Consider improving semantic matching")
        print("  - Review cross-encoder reranking parameters")

if __name__ == "__main__":
    main()
