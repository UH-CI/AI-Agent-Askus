#!/usr/bin/env python3
"""
Evaluation V4 - Testing with k=50 configuration
Similar to V3 but with improved retrieval settings
"""

import json
import requests
import time
from datetime import datetime
from typing import List, Dict, Any
import os

def send_question_to_api(question: str, api_url: str = "http://localhost:8001/askus/invoke", timeout: int = 60) -> Dict[str, Any]:
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
        start_time = time.time()
        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            output = result.get('output', {})
            message = output.get('message', {})
            assistant_response = message.get('content', '')
            sources = output.get('sources', [])
            
            return {
                "success": True,
                "answer": assistant_response,
                "response_time": response_time,
                "status_code": response.status_code,
                "sources": sources,
                "source_count": len(sources),
                "answer_length": len(assistant_response),
                "contains_sorry": "sorry" in assistant_response.lower() and "don't have" in assistant_response.lower()
            }
        else:
            return {
                "success": False, 
                "error": f"HTTP {response.status_code}: {response.text}",
                "response_time": time.time() - start_time,
                "status_code": response.status_code,
                "sources": [],
                "source_count": 0,
                "answer_length": 0,
                "contains_sorry": False
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False, 
            "error": f"Request failed: {str(e)}",
            "response_time": 0,
            "status_code": 0,
            "sources": [],
            "source_count": 0,
            "answer_length": 0,
            "contains_sorry": False
        }

def evaluate_answer(question: str, answer: str, expected_keywords: List[str], sources: List[str]) -> Dict[str, Any]:
    """Evaluate the quality of an answer"""
    
    # Check for keyword coverage
    keywords_found = []
    keywords_missing = []
    
    answer_lower = answer.lower()
    for keyword in expected_keywords:
        if keyword.lower() in answer_lower:
            keywords_found.append(keyword)
        else:
            keywords_missing.append(keyword)
    
    keyword_coverage = len(keywords_found) / len(expected_keywords) if expected_keywords else 0
    
    # Check if answer contains "sorry" response
    contains_sorry = "sorry" in answer_lower and "don't have" in answer_lower
    
    # Determine if question was answered
    answered = not contains_sorry and len(answer.strip()) > 0
    
    return {
        "answered": answered,
        "keywords_found": keywords_found,
        "keywords_missing": keywords_missing,
        "keyword_coverage": keyword_coverage
    }

def load_evaluation_questions(file_path: str) -> List[Dict[str, Any]]:
    """Load evaluation questions from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions = []
    
    # Handle the nested structure from evaluation_questions.json
    if 'evaluation_questions' in data:
        for article in data['evaluation_questions']:
            article_url = article.get('url', '')
            for question_data in article.get('questions', []):
                questions.append({
                    'question': question_data.get('question', ''),
                    'expected_answer_contains': question_data.get('expected_answer_contains', []),
                    'article_url': article_url
                })
    else:
        # Handle direct list format
        questions = data
    
    return questions

def run_evaluation():
    """Run the complete evaluation"""
    
    print("🚀 Starting Evaluation V4 - k=50 Configuration")
    print("=" * 80)
    
    # Load evaluation questions
    questions_file = "/home/exouser/AI-Agent-Askus/evaluation/evaluation_questions.json"
    
    if not os.path.exists(questions_file):
        print(f"❌ Error: Questions file not found at {questions_file}")
        return
    
    try:
        questions = load_evaluation_questions(questions_file)
        print(f"📋 Loaded {len(questions)} questions for evaluation")
    except Exception as e:
        print(f"❌ Error loading questions: {e}")
        return
    
    # Initialize results structure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "evaluation_version": "V4",
        "timestamp": timestamp,
        "evaluation_metadata": {
            "configuration": {
                "retriever_k": 50,
                "max_sources": 5,
                "search_type": "similarity",
                "cross_encoder_reranking": True
            },
            "total_questions": len(questions),
            "api_endpoint": "http://localhost:8001/askus/invoke"
        },
        "articles": []
    }
    
    # Group questions by article
    articles_dict = {}
    for i, q in enumerate(questions):
        article_url = q.get('article_url', f'unknown_article_{i}')
        if article_url not in articles_dict:
            articles_dict[article_url] = {
                "article_url": article_url,
                "article_index": len(articles_dict),
                "question_results": []
            }
        articles_dict[article_url]["question_results"].append(q)
    
    # Process each article
    total_questions = 0
    successful_responses = 0
    failed_responses = 0
    total_response_time = 0
    total_keyword_coverage = 0
    
    for article_url, article_data in articles_dict.items():
        print(f"\n📄 Processing article: {article_url}")
        print(f"   Questions: {len(article_data['question_results'])}")
        
        article_results = {
            "article_url": article_url,
            "article_index": article_data["article_index"],
            "question_results": []
        }
        
        article_successful = 0
        article_failed = 0
        article_response_time = 0
        article_keyword_coverage = 0
        
        for question_data in article_data["question_results"]:
            question = question_data["question"]
            expected_keywords = question_data.get("expected_answer_contains", [])
            
            print(f"   ❓ Testing: {question[:60]}...")
            
            # Send question to API
            api_response = send_question_to_api(question)
            
            # Evaluate response
            if api_response["success"]:
                evaluation = evaluate_answer(
                    question, 
                    api_response["answer"], 
                    expected_keywords,
                    api_response["sources"]
                )
                
                # Add response time and other metrics to evaluation
                evaluation.update({
                    "response_time": api_response["response_time"],
                    "answer_length": api_response["answer_length"],
                    "source_count": api_response["source_count"],
                    "contains_sorry": api_response["contains_sorry"]
                })
                
                if evaluation["answered"]:
                    article_successful += 1
                    successful_responses += 1
                else:
                    article_failed += 1
                    failed_responses += 1
                
                article_response_time += api_response["response_time"]
                article_keyword_coverage += evaluation["keyword_coverage"]
                
                # Determine response type
                if evaluation["contains_sorry"]:
                    response_type = "❌ Sorry"
                else:
                    response_type = "✅ Real answer"
                
                print(f"      {response_type}: {api_response['response_time']:.2f}s, "
                      f"Sources: {api_response['source_count']}, "
                      f"Keywords: {evaluation['keyword_coverage']:.1%}")
            else:
                evaluation = {
                    "answered": False,
                    "response_time": api_response.get("response_time", 0),
                    "answer_length": 0,
                    "source_count": 0,
                    "contains_sorry": False,
                    "keywords_found": [],
                    "keywords_missing": expected_keywords,
                    "keyword_coverage": 0.0
                }
                article_failed += 1
                failed_responses += 1
                print(f"      ❌ Failed: {api_response.get('error', 'Unknown error')}")
            
            # Store result
            question_result = {
                "question": question,
                "expected_answer_contains": expected_keywords,
                "api_response": api_response,
                "evaluation": evaluation,
                "timestamp": datetime.now().isoformat()
            }
            
            article_results["question_results"].append(question_result)
            total_questions += 1
            total_response_time += evaluation["response_time"]
            total_keyword_coverage += evaluation["keyword_coverage"]
            
            # Brief pause between questions
            time.sleep(0.5)
        
        # Calculate article summary
        article_results["article_summary"] = {
            "total_questions": len(article_data["question_results"]),
            "successful_responses": article_successful,
            "failed_responses": article_failed,
            "average_response_time": article_response_time / len(article_data["question_results"]) if article_data["question_results"] else 0,
            "average_keyword_coverage": article_keyword_coverage / len(article_data["question_results"]) if article_data["question_results"] else 0
        }
        
        results["articles"].append(article_results)
    
    # Calculate overall summary
    results["evaluation_summary"] = {
        "total_questions": total_questions,
        "successful_responses": successful_responses,
        "failed_responses": failed_responses,
        "success_rate": successful_responses / total_questions if total_questions > 0 else 0,
        "average_response_time": total_response_time / total_questions if total_questions > 0 else 0,
        "average_keyword_coverage": total_keyword_coverage / total_questions if total_questions > 0 else 0
    }
    
    # Save results
    output_file = f"/home/exouser/AI-Agent-Askus/evaluation/evaluation_results_V4_{timestamp}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Evaluation V4 completed!")
        print(f"📊 Results saved to: {output_file}")
        print(f"\n📈 SUMMARY:")
        print(f"   Total questions: {total_questions}")
        print(f"   Successful responses: {successful_responses}")
        print(f"   Failed responses: {failed_responses}")
        print(f"   Success rate: {successful_responses/total_questions:.1%}")
        print(f"   Average response time: {total_response_time/total_questions:.2f}s")
        print(f"   Average keyword coverage: {total_keyword_coverage/total_questions:.1%}")
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")

if __name__ == "__main__":
    run_evaluation()
