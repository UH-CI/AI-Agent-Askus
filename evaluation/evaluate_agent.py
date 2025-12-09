#!/usr/bin/env python3
"""
Evaluate the AI agent by sending generated questions to the API and collecting responses
"""

import json
import os
import sys
import time
import requests
from typing import List, Dict, Any
from datetime import datetime

def load_evaluation_questions(file_path: str) -> Dict[str, Any]:
    """Load the generated evaluation questions"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_questions = sum(len(article.get('questions', [])) for article in data.get('evaluation_questions', []))
        print(f"✅ Loaded {len(data.get('evaluation_questions', []))} article sets with {total_questions} total questions")
        return data
    except Exception as e:
        print(f"❌ Error loading evaluation questions: {e}")
        return {}

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
        print(f"🔄 Sending question: {question[:80]}...")
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the answer from the response structure
            output = result.get('output', {})
            message = output.get('message', {})
            
            # Get the assistant's response content
            assistant_response = message.get('content', '')
            
            if assistant_response:
                print(f"✅ Received response ({len(assistant_response)} chars)")
                return {
                    "success": True,
                    "answer": assistant_response,
                    "response_time": response.elapsed.total_seconds(),
                    "status_code": response.status_code,
                    "sources": output.get('sources', [])  # Include sources if available
                }
            else:
                print(f"❌ No assistant response found in API output")
                return {
                    "success": False,
                    "error": "No assistant response found",
                    "raw_response": result,
                    "status_code": response.status_code
                }
        else:
            print(f"❌ API error: {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "status_code": response.status_code
            }
            
    except requests.exceptions.Timeout:
        print(f"❌ Request timeout after {timeout} seconds")
        return {
            "success": False,
            "error": f"Request timeout after {timeout} seconds"
        }
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error - is the API server running?")
        return {
            "success": False,
            "error": "Connection error - API server not reachable"
        }
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def evaluate_single_question(question_data: Dict[str, Any], api_url: str) -> Dict[str, Any]:
    """Evaluate a single question and return the result"""
    
    question = question_data.get('question', '')
    expected_contains = question_data.get('expected_answer_contains', [])
    
    # Send question to API
    api_response = send_question_to_api(question, api_url)
    
    # Analyze the response
    evaluation_result = {
        "question": question,
        "expected_answer_contains": expected_contains,
        "api_response": api_response,
        "evaluation": {
            "answered": api_response.get('success', False),
            "response_time": api_response.get('response_time', 0),
            "answer_length": len(api_response.get('answer', '')) if api_response.get('success') else 0
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Check if expected keywords are present (simple keyword matching)
    if api_response.get('success') and api_response.get('answer'):
        answer = api_response['answer'].lower()
        keywords_found = []
        keywords_missing = []
        
        for keyword in expected_contains:
            if keyword.lower() in answer:
                keywords_found.append(keyword)
            else:
                keywords_missing.append(keyword)
        
        evaluation_result["evaluation"].update({
            "keywords_found": keywords_found,
            "keywords_missing": keywords_missing,
            "keyword_coverage": len(keywords_found) / len(expected_contains) if expected_contains else 1.0
        })
    
    return evaluation_result

def save_evaluation_results(results: Dict[str, Any], output_file: str):
    """Save evaluation results to file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved evaluation results to {output_file}")
    except Exception as e:
        print(f"❌ Error saving results: {e}")

def main():
    """Main evaluation function"""
    
    # Configuration
    questions_file = "/home/exouser/AI-Agent-Askus/evaluation/evaluation_questions.json"
    output_file = "/home/exouser/AI-Agent-Askus/evaluation/agent_evaluation_results.json"
    api_url = "http://localhost:8001/askus/invoke"
    
    print("🚀 Starting AI Agent Evaluation")
    print("=" * 60)
    
    # Load evaluation questions
    questions_data = load_evaluation_questions(questions_file)
    if not questions_data or not questions_data.get('evaluation_questions'):
        print("❌ No evaluation questions found, exiting")
        sys.exit(1)
    
    # Test API connectivity
    print("🔍 Testing API connectivity...")
    test_response = send_question_to_api("Hello, can you help me?", api_url)
    if not test_response.get('success'):
        print(f"❌ API test failed: {test_response.get('error')}")
        print("Make sure the AI agent is running on http://localhost:8001")
        sys.exit(1)
    print("✅ API connectivity confirmed")
    
    # Initialize results structure
    evaluation_results = {
        "evaluation_metadata": {
            "started_at": datetime.now().isoformat(),
            "questions_source": questions_file,
            "api_endpoint": api_url,
            "total_articles": len(questions_data.get('evaluation_questions', [])),
            "total_questions": sum(len(article.get('questions', [])) for article in questions_data.get('evaluation_questions', []))
        },
        "article_evaluations": [],
        "summary_statistics": {}
    }
    
    # Process each article's questions
    total_processed = 0
    total_successful = 0
    total_failed = 0
    
    for article_idx, article_data in enumerate(questions_data.get('evaluation_questions', [])):
        article_url = article_data.get('article_url', 'Unknown')
        article_questions = article_data.get('questions', [])
        
        print(f"\n📄 Processing article {article_idx + 1}: {article_url[:80]}...")
        
        article_evaluation = {
            "article_url": article_url,
            "article_index": article_data.get('article_index', article_idx),
            "content_preview": article_data.get('content_preview', ''),
            "question_results": [],
            "article_summary": {
                "total_questions": len(article_questions),
                "successful_responses": 0,
                "failed_responses": 0,
                "average_response_time": 0,
                "average_keyword_coverage": 0
            }
        }
        
        # Process each question in the article
        response_times = []
        keyword_coverages = []
        
        for q_idx, question_data in enumerate(article_questions):
            print(f"  Question {q_idx + 1}/{len(article_questions)}")
            
            result = evaluate_single_question(question_data, api_url)
            article_evaluation["question_results"].append(result)
            
            total_processed += 1
            
            if result["api_response"].get("success"):
                total_successful += 1
                response_times.append(result["api_response"].get("response_time", 0))
                if "keyword_coverage" in result.get("evaluation", {}):
                    keyword_coverages.append(result["evaluation"]["keyword_coverage"])
            else:
                total_failed += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        # Calculate article summary statistics
        article_evaluation["article_summary"]["successful_responses"] = sum(1 for r in article_evaluation["question_results"] if r["api_response"].get("success"))
        article_evaluation["article_summary"]["failed_responses"] = len(article_questions) - article_evaluation["article_summary"]["successful_responses"]
        article_evaluation["article_summary"]["average_response_time"] = sum(response_times) / len(response_times) if response_times else 0
        article_evaluation["article_summary"]["average_keyword_coverage"] = sum(keyword_coverages) / len(keyword_coverages) if keyword_coverages else 0
        
        evaluation_results["article_evaluations"].append(article_evaluation)
        
        # Save incrementally every 10 articles
        if (article_idx + 1) % 10 == 0:
            save_evaluation_results(evaluation_results, output_file)
            print(f"📊 Progress: {article_idx + 1}/{len(questions_data.get('evaluation_questions', []))} articles processed")
    
    # Calculate final summary statistics
    evaluation_results["summary_statistics"] = {
        "completed_at": datetime.now().isoformat(),
        "total_questions_processed": total_processed,
        "successful_responses": total_successful,
        "failed_responses": total_failed,
        "success_rate": total_successful / total_processed if total_processed > 0 else 0,
        "total_articles_processed": len(evaluation_results["article_evaluations"])
    }
    
    # Final save
    save_evaluation_results(evaluation_results, output_file)
    
    print("\n" + "=" * 60)
    print("✅ Evaluation Complete!")
    print(f"📊 Total questions processed: {total_processed}")
    print(f"✅ Successful responses: {total_successful}")
    print(f"❌ Failed responses: {total_failed}")
    print(f"📈 Success rate: {(total_successful / total_processed * 100):.1f}%" if total_processed > 0 else "N/A")
    print(f"💾 Results saved to: {output_file}")

if __name__ == "__main__":
    main()
