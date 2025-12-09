#!/usr/bin/env python3
"""
Test the failed questions from the retest file to see improvements after TeamDynamix ingestion
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

def analyze_improvement(old_result, new_result):
    """Compare old and new results to see improvements"""
    
    old_answer = old_result.get('answer', '')
    new_answer = new_result.get('answer', '')
    
    old_is_sorry = "sorry" in old_answer.lower() and "don't have" in old_answer.lower()
    new_is_sorry = "sorry" in new_answer.lower() and "don't have" in new_answer.lower()
    
    old_sources = old_result.get('sources', [])
    new_sources = new_result.get('sources', [])
    
    # Count TeamDynamix sources
    old_teamdx = sum(1 for s in old_sources if 'teamdynamix.com' in str(s))
    new_teamdx = sum(1 for s in new_sources if 'teamdynamix.com' in str(s))
    
    improvement_status = "🔄 NO CHANGE"
    if old_is_sorry and not new_is_sorry:
        improvement_status = "🎉 MAJOR IMPROVEMENT"
    elif old_is_sorry and new_is_sorry and new_teamdx > old_teamdx:
        improvement_status = "📈 MINOR IMPROVEMENT"
    elif not old_is_sorry and not new_is_sorry and new_teamdx > old_teamdx:
        improvement_status = "📊 SOURCE IMPROVEMENT"
    elif not old_is_sorry and new_is_sorry:
        improvement_status = "📉 REGRESSION"
    
    return {
        "status": improvement_status,
        "old_sorry": old_is_sorry,
        "new_sorry": new_is_sorry,
        "old_teamdx_sources": old_teamdx,
        "new_teamdx_sources": new_teamdx,
        "answer_length_change": len(new_answer) - len(old_answer)
    }

def main():
    # Load the failed questions
    with open('/home/exouser/AI-Agent-Askus/evaluation/failed_questions_retest.json', 'r') as f:
        failed_data = json.load(f)
    
    print("🔄 Retesting Failed Questions After TeamDynamix Ingestion")
    print("=" * 80)
    
    results = []
    improvements = 0
    regressions = 0
    no_changes = 0
    
    for i, old_result in enumerate(failed_data['results'], 1):
        question = old_result['question']
        source_article = old_result['source_article']
        
        print(f"\n📝 Question {i}: {question}")
        print(f"📄 Source Article: {source_article}")
        print("-" * 60)
        
        # Test the question
        new_result = send_question_to_api(question)
        
        if new_result["success"]:
            # Analyze improvement
            analysis = analyze_improvement(old_result, new_result)
            
            print(f"{analysis['status']}")
            print(f"⏱️  Response time: {new_result['response_time']:.2f} seconds")
            
            # Show answer comparison
            old_answer = old_result['answer'][:100] + "..." if len(old_result['answer']) > 100 else old_result['answer']
            new_answer = new_result['answer'][:100] + "..." if len(new_result['answer']) > 100 else new_result['answer']
            
            print(f"📜 Old answer: {old_answer}")
            print(f"📝 New answer: {new_answer}")
            
            # Show source comparison
            old_sources = old_result.get('sources', [])
            new_sources = new_result.get('sources', [])
            
            old_teamdx = [s for s in old_sources if 'teamdynamix.com' in str(s)]
            new_teamdx = [s for s in new_sources if 'teamdynamix.com' in str(s)]
            
            print(f"📊 Sources - Old: {len(old_sources)} ({len(old_teamdx)} TeamDX), New: {len(new_sources)} ({len(new_teamdx)} TeamDX)")
            
            if new_teamdx:
                print(f"🎯 New TeamDynamix sources:")
                for j, source in enumerate(new_teamdx, 1):
                    if 'ID=' in source:
                        article_id = source.split('ID=')[1].split('&')[0]
                        print(f"   {j}. Article ID {article_id}")
            
            # Count improvements
            if "MAJOR IMPROVEMENT" in analysis['status']:
                improvements += 1
            elif "REGRESSION" in analysis['status']:
                regressions += 1
            else:
                no_changes += 1
                
            results.append({
                "question": question,
                "old_result": old_result,
                "new_result": new_result,
                "analysis": analysis
            })
            
        else:
            print(f"❌ Query failed: {new_result['error']}")
            regressions += 1
        
        print("\n" + "🔄" * 60)
    
    # Summary
    print(f"\n📊 OVERALL SUMMARY")
    print("=" * 80)
    print(f"🎉 Major Improvements: {improvements}")
    print(f"🔄 No Changes: {no_changes}")
    print(f"📉 Regressions: {regressions}")
    print(f"📈 Total Questions: {len(failed_data['results'])}")
    
    if improvements > 0:
        improvement_rate = (improvements / len(failed_data['results'])) * 100
        print(f"✅ Improvement Rate: {improvement_rate:.1f}%")
    
    # Show most improved questions
    major_improvements = [r for r in results if "MAJOR IMPROVEMENT" in r['analysis']['status']]
    if major_improvements:
        print(f"\n🏆 QUESTIONS WITH MAJOR IMPROVEMENTS:")
        for i, result in enumerate(major_improvements, 1):
            print(f"   {i}. {result['question'][:60]}...")

if __name__ == "__main__":
    main()
