#!/usr/bin/env python3
"""
V3 Evaluation of the AI Agent - Enhanced Testing with Performance Metrics
This evaluation includes additional metrics and improved analysis
"""

import json
import requests
import time
from typing import List, Dict, Any
import os
from datetime import datetime

def send_question_to_api(question: str, api_url: str = "http://localhost:8001/askus/invoke", timeout: int = 30) -> Dict[str, Any]:
    """Send a question to the AI agent API and return the response with enhanced metrics"""
    
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
    
    start_time = time.time()
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            output = result.get('output', {})
            message = output.get('message', {})
            assistant_response = message.get('content', '')
            
            if assistant_response:
                return {
                    "success": True,
                    "answer": assistant_response,
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "sources": output.get('sources', []),
                    "source_count": len(output.get('sources', [])),
                    "answer_length": len(assistant_response),
                    "contains_sorry": "I'm sorry I don't have the answer" in assistant_response
                }
            else:
                return {
                    "success": False, 
                    "error": "No response content",
                    "response_time": response_time,
                    "status_code": response.status_code
                }
        else:
            return {
                "success": False, 
                "error": f"HTTP {response.status_code}",
                "response_time": response_time,
                "status_code": response.status_code
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False, 
            "error": "Request timeout",
            "response_time": timeout
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False, 
            "error": "Connection error - API not available"
        }
    except Exception as e:
        return {
            "success": False, 
            "error": f"Unexpected error: {str(e)}"
        }

def evaluate_answer(api_response: Dict[str, Any], expected_keywords: List[str]) -> Dict[str, Any]:
    """Enhanced evaluation of the API response against expected keywords"""
    
    if not api_response.get("success", False):
        return {
            "answered": False,
            "response_time": api_response.get("response_time", 0),
            "error": api_response.get("error", "Unknown error"),
            "keywords_found": [],
            "keywords_missing": expected_keywords,
            "keyword_coverage": 0.0,
            "answer_length": 0,
            "source_count": 0,
            "contains_sorry": True
        }
    
    answer = api_response.get("answer", "").lower()
    keywords_found = []
    keywords_missing = []
    
    for keyword in expected_keywords:
        if keyword.lower() in answer:
            keywords_found.append(keyword)
        else:
            keywords_missing.append(keyword)
    
    keyword_coverage = len(keywords_found) / len(expected_keywords) if expected_keywords else 0.0
    
    return {
        "answered": True,
        "response_time": api_response.get("response_time", 0),
        "answer_length": api_response.get("answer_length", 0),
        "source_count": api_response.get("source_count", 0),
        "contains_sorry": api_response.get("contains_sorry", False),
        "keywords_found": keywords_found,
        "keywords_missing": keywords_missing,
        "keyword_coverage": keyword_coverage
    }

def run_v3_evaluation():
    """Run the V3 evaluation with enhanced metrics and analysis"""
    
    print("🚀 Starting V3 Evaluation...")
    print("=" * 60)
    
    # Load evaluation questions
    try:
        with open('evaluation_questions.json', 'r') as f:
            questions_file = json.load(f)
            questions_data = questions_file.get('evaluation_questions', [])
    except FileNotFoundError:
        print("❌ evaluation_questions.json not found!")
        return
    
    results = {
        "evaluation_version": "V3",
        "timestamp": datetime.now().isoformat(),
        "evaluation_metadata": {
            "total_articles": len(questions_data),
            "api_endpoint": "http://localhost:8001/askus/invoke",
            "timeout": 30
        },
        "articles": [],
        "summary": {}
    }
    
    total_questions = 0
    successful_responses = 0
    failed_responses = 0
    total_response_time = 0
    total_keyword_coverage = 0
    answered_questions = 0
    sorry_responses = 0
    
    for article_idx, article in enumerate(questions_data):
        print(f"\n📄 Processing Article {article_idx + 1}/{len(questions_data)}")
        print(f"URL: {article.get('url', 'N/A')}")
        
        article_result = {
            "article_url": article.get('url', ''),
            "article_index": article_idx,
            "content_preview": article.get('content', '')[:200] + "..." if len(article.get('content', '')) > 200 else article.get('content', ''),
            "question_results": []
        }
        
        article_questions = 0
        article_successful = 0
        article_response_time = 0
        article_keyword_coverage = 0
        
        for question_data in article.get('questions', []):
            question = question_data.get('question', '')
            expected_keywords = question_data.get('expected_answer_contains', [])
            
            print(f"  ❓ Testing: {question[:80]}...")
            
            # Send question to API
            api_response = send_question_to_api(question)
            
            # Evaluate response
            evaluation = evaluate_answer(api_response, expected_keywords)
            
            # Compile result
            question_result = {
                "question": question,
                "expected_answer_contains": expected_keywords,
                "api_response": api_response,
                "evaluation": evaluation,
                "timestamp": datetime.now().isoformat()
            }
            
            article_result["question_results"].append(question_result)
            
            # Update counters
            total_questions += 1
            article_questions += 1
            
            if api_response.get("success", False):
                successful_responses += 1
                article_successful += 1
                answered_questions += 1
                
                if api_response.get("contains_sorry", False):
                    sorry_responses += 1
            else:
                failed_responses += 1
            
            response_time = evaluation.get("response_time", 0)
            total_response_time += response_time
            article_response_time += response_time
            
            keyword_coverage = evaluation.get("keyword_coverage", 0)
            total_keyword_coverage += keyword_coverage
            article_keyword_coverage += keyword_coverage
            
            # Brief pause between questions
            time.sleep(0.5)
        
        # Calculate article summary
        article_result["article_summary"] = {
            "total_questions": article_questions,
            "successful_responses": article_successful,
            "failed_responses": article_questions - article_successful,
            "average_response_time": article_response_time / article_questions if article_questions > 0 else 0,
            "average_keyword_coverage": article_keyword_coverage / article_questions if article_questions > 0 else 0
        }
        
        results["articles"].append(article_result)
        
        print(f"  ✅ Article completed: {article_successful}/{article_questions} successful")
    
    # Calculate overall summary
    results["summary"] = {
        "total_questions": total_questions,
        "successful_responses": successful_responses,
        "failed_responses": failed_responses,
        "answered_questions": answered_questions,
        "sorry_responses": sorry_responses,
        "actual_answers": successful_responses - sorry_responses,
        "success_rate": (successful_responses / total_questions * 100) if total_questions > 0 else 0,
        "actual_answer_rate": ((successful_responses - sorry_responses) / total_questions * 100) if total_questions > 0 else 0,
        "average_response_time": total_response_time / total_questions if total_questions > 0 else 0,
        "average_keyword_coverage": total_keyword_coverage / total_questions if total_questions > 0 else 0
    }
    
    # Save results
    output_filename = f"evaluation_results_V3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🎉 V3 EVALUATION COMPLETE!")
    print("=" * 60)
    print(f"📊 Total Questions: {total_questions}")
    print(f"✅ Successful Responses: {successful_responses}")
    print(f"❌ Failed Responses: {failed_responses}")
    print(f"💬 Actual Answers (non-sorry): {successful_responses - sorry_responses}")
    print(f"😞 Sorry Responses: {sorry_responses}")
    print(f"📈 Success Rate: {results['summary']['success_rate']:.1f}%")
    print(f"🎯 Actual Answer Rate: {results['summary']['actual_answer_rate']:.1f}%")
    print(f"⏱️  Average Response Time: {results['summary']['average_response_time']:.2f}s")
    print(f"🔍 Average Keyword Coverage: {results['summary']['average_keyword_coverage']:.1f}%")
    print(f"💾 Results saved to: {output_filename}")
    print("=" * 60)

if __name__ == "__main__":
    run_v3_evaluation()
