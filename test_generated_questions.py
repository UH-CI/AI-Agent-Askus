#!/usr/bin/env python3
"""
Test 100 randomly sampled questions from the generated evaluation questions
"""

import json
import random
import requests
import time
from typing import List, Dict, Any
from datetime import datetime

def load_generated_questions(file_path: str) -> List[Dict[str, Any]]:
    """Load the generated evaluation questions"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions_data = data.get('evaluation_questions', [])
        print(f"✅ Loaded {len(questions_data)} question sets from {file_path}")
        return questions_data
    except Exception as e:
        print(f"❌ Error loading questions: {e}")
        return []

def extract_all_questions(questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract all individual questions from the question sets"""
    all_questions = []
    
    for question_set in questions_data:
        article_url = question_set.get('article_url', 'Unknown')
        article_index = question_set.get('article_index', -1)
        questions = question_set.get('questions', [])
        
        for question in questions:
            all_questions.append({
                'question': question.get('question', ''),
                'expected_answer_contains': question.get('expected_answer_contains', []),
                'article_url': article_url,
                'article_index': article_index,
                'generated_at': question_set.get('generated_at', '')
            })
    
    return all_questions

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
                "sources": sources,
                "raw_response": result,
                "status_code": response.status_code
            }
        else:
            return {
                "success": False, 
                "error": f"HTTP {response.status_code}: {response.text}",
                "status_code": response.status_code,
                "response_time": time.time() - start_time
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False, 
            "error": f"Request failed: {str(e)}",
            "response_time": time.time() - start_time
        }

def evaluate_response(question_data: Dict[str, Any], api_response: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate the API response against expected criteria"""
    
    if not api_response.get("success", False):
        return {
            "answered": False,
            "keywords_found": [],
            "keywords_missing": question_data.get('expected_answer_contains', []),
            "keyword_coverage": 0.0,
            "response_time": api_response.get('response_time', 0),
            "answer_length": 0,
            "source_count": 0,
            "contains_sorry": False,
            "error": api_response.get('error', 'Unknown error')
        }
    
    answer = api_response.get('answer', '').lower()
    expected_keywords = question_data.get('expected_answer_contains', [])
    sources = api_response.get('sources', [])
    
    # Check for "sorry" responses
    contains_sorry = "sorry" in answer and "don't have" in answer
    
    # Check keyword coverage
    keywords_found = []
    keywords_missing = []
    
    for keyword in expected_keywords:
        if keyword.lower() in answer:
            keywords_found.append(keyword)
        else:
            keywords_missing.append(keyword)
    
    keyword_coverage = len(keywords_found) / len(expected_keywords) if expected_keywords else 1.0
    
    # Check if TeamDynamix sources are present
    teamdx_sources = [s for s in sources if isinstance(s, str) and 'teamdynamix.com' in s]
    
    return {
        "answered": not contains_sorry and keyword_coverage > 0,
        "keywords_found": keywords_found,
        "keywords_missing": keywords_missing,
        "keyword_coverage": keyword_coverage,
        "response_time": api_response.get('response_time', 0),
        "answer_length": len(api_response.get('answer', '')),
        "source_count": len(sources),
        "teamdx_source_count": len(teamdx_sources),
        "contains_sorry": contains_sorry
    }

def main():
    """Main function to test 100 random questions"""
    
    # Configuration
    questions_file = "/home/exouser/AI-Agent-Askus/evaluation/evaluation_questions.json"
    output_file = f"/home/exouser/AI-Agent-Askus/evaluation/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    sample_size = 100
    
    print("🚀 Starting Random Question Testing")
    print("=" * 60)
    print(f"📁 Questions file: {questions_file}")
    print(f"📊 Sample size: {sample_size}")
    print(f"💾 Output file: {output_file}")
    print()
    
    # Load questions
    questions_data = load_generated_questions(questions_file)
    if not questions_data:
        print("❌ No questions loaded, exiting")
        return
    
    # Extract all individual questions
    all_questions = extract_all_questions(questions_data)
    print(f"📋 Total individual questions available: {len(all_questions)}")
    
    if len(all_questions) < sample_size:
        print(f"⚠️  Only {len(all_questions)} questions available, using all of them")
        sample_size = len(all_questions)
    
    # Randomly sample questions
    sampled_questions = random.sample(all_questions, sample_size)
    print(f"🎲 Randomly sampled {len(sampled_questions)} questions")
    print()
    
    # Test each question
    results = []
    successful_tests = 0
    failed_tests = 0
    
    for i, question_data in enumerate(sampled_questions, 1):
        question = question_data['question']
        print(f"🔍 Testing question {i}/{sample_size}")
        print(f"❓ Question: {question}")
        
        # Send to API
        api_response = send_question_to_api(question)
        
        # Evaluate response
        evaluation = evaluate_response(question_data, api_response)
        
        # Store result
        result = {
            "question_number": i,
            "question_data": question_data,
            "api_response": api_response,
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat()
        }
        results.append(result)
        
        # Print summary
        if api_response.get("success", False):
            if evaluation["answered"]:
                print(f"✅ SUCCESS: Answered with {evaluation['keyword_coverage']:.1%} keyword coverage")
                successful_tests += 1
            else:
                if evaluation["contains_sorry"]:
                    print(f"⚠️  PARTIAL: Retrieved sources but gave 'sorry' response")
                else:
                    print(f"❌ FAILED: Poor keyword coverage ({evaluation['keyword_coverage']:.1%})")
                failed_tests += 1
        else:
            print(f"❌ ERROR: {api_response.get('error', 'Unknown error')}")
            failed_tests += 1
        
        print(f"⏱️  Response time: {evaluation['response_time']:.2f}s")
        print(f"📊 Sources: {evaluation['source_count']} total, {evaluation.get('teamdx_source_count', 0)} TeamDynamix")
        print()
        
        # Save incrementally every 10 questions
        if i % 10 == 0:
            save_results(results, output_file, i, sample_size)
        
        # Small delay to avoid overwhelming the API
        time.sleep(0.5)
    
    # Final save
    save_results(results, output_file, sample_size, sample_size)
    
    # Print final summary
    print("=" * 60)
    print("🎉 Testing Complete!")
    print(f"📊 Results: {successful_tests} successful, {failed_tests} failed")
    print(f"📈 Success rate: {successful_tests/sample_size:.1%}")
    print(f"💾 Full results saved to: {output_file}")

def save_results(results: List[Dict[str, Any]], output_file: str, current: int, total: int):
    """Save results to file"""
    try:
        summary = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "questions_tested": current,
                "total_planned": total,
                "source_file": "/home/exouser/AI-Agent-Askus/evaluation/evaluation_questions.json"
            },
            "results": results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Progress saved: {current}/{total} questions tested")
    except Exception as e:
        print(f"❌ Error saving results: {e}")

if __name__ == "__main__":
    main()
