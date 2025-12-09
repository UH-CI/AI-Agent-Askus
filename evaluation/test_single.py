#!/usr/bin/env python3
"""
Test script to debug the question generation with a single article
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_single_article():
    # Load data
    with open('/home/exouser/AI-Agent-Askus/web-scraper/data/teamdynamix.json', 'r') as f:
        articles = json.load(f)
    
    # Find first processable article
    test_article = None
    for article in articles:
        content = article.get('extracted', '')
        if (len(content.strip()) >= 100 and 
            '1-2 bullets describing the problem' not in content and 
            'Numbered list so people can reference steps' not in content):
            test_article = article
            break
    
    if not test_article:
        print("❌ No processable article found")
        return
    
    print(f"Testing with article: {test_article['url']}")
    print(f"Content length: {len(test_article['extracted'])}")
    print(f"Content preview: {test_article['extracted'][:200]}...")
    print()
    
    # Test OpenAI API
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found")
        return
    
    print(f"API key found: {api_key[:10]}...")
    
    client = OpenAI(api_key=api_key)
    
    try:
        prompt = f"""Based on the following knowledge base article content, create 1-2 specific, answerable questions that test understanding of the information provided.

Article Content:
{test_article['extracted']}

Please respond with a JSON object in this exact format:
{{
    "questions": [
        {{
            "question": "Your first question here",
            "expected_answer_contains": ["key", "concepts"]
        }}
    ]
}}"""

        print("🔄 Making API call...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at creating evaluation questions. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content.strip()
        print("✅ API call successful!")
        print(f"Response: {response_text}")
        
        # Try to parse JSON
        try:
            questions_data = json.loads(response_text)
            print("✅ JSON parsing successful!")
            print(f"Generated questions: {json.dumps(questions_data, indent=2)}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            
    except Exception as e:
        print(f"❌ API call failed: {e}")

if __name__ == "__main__":
    test_single_article()
