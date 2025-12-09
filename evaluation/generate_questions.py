#!/usr/bin/env python3
"""
Generate evaluation questions from TeamDynamix knowledge base articles using GPT-4o
Uses the web-scraper extracted data from kb_articles_extracted.json
"""

import json
import os
import sys
import time
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_teamdynamix_data(file_path: str) -> List[Dict[str, Any]]:
    """Load the TeamDynamix JSON data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} TeamDynamix articles")
        return data
    except Exception as e:
        print(f"❌ Error loading TeamDynamix data: {e}")
        return []

def create_question_prompt(article_content: str, article_url: str) -> str:
    """Create a prompt for GPT-4o to generate questions based on article content"""
    return f"""Based on the following knowledge base article content, create 1-2 specific, answerable questions that test understanding of the information provided. The questions should:

1. Be directly answerable from the content provided
2. Test practical knowledge (how-to, troubleshooting, procedures)
3. Be realistic questions a user might ask
4. Avoid yes/no questions when possible
5. Focus on actionable information

Article URL: {article_url}

Article Content:
{article_content}

Please respond with a JSON object in this exact format:
{{
    "questions": [
        {{
            "question": "Your first question here",
            "expected_answer_contains": ["key", "concepts", "that", "should", "be", "in", "answer"]
        }},
        {{
            "question": "Your second question here (optional)",
            "expected_answer_contains": ["key", "concepts", "that", "should", "be", "in", "answer"]
        }}
    ]
}}

Only include questions that can be clearly answered from the provided content."""

def generate_questions_for_article(client: OpenAI, article: Dict[str, Any], article_index: int) -> Dict[str, Any]:
    """Generate questions for a single article using GPT-4o"""
    
    url = article.get('url', 'Unknown URL')
    content = article.get('extracted', '')
    
    # Skip articles with very little content
    if len(content.strip()) < 100:
        print(f"⏭️  Skipping article {article_index + 1} (too short): {url}")
        return None
    
    # Skip template articles (they contain placeholder text)
    if "1-2 bullets describing the problem" in content or "Numbered list so people can reference steps" in content:
        print(f"⏭️  Skipping template article {article_index + 1}: {url}")
        return None
    
    print(f"🔄 Processing article {article_index + 1}: {url[:80]}...")
    
    try:
        prompt = create_question_prompt(content, url)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at creating evaluation questions for knowledge base articles. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith('```'):
            response_text = response_text[3:]   # Remove ```
        if response_text.endswith('```'):
            response_text = response_text[:-3]  # Remove closing ```
        response_text = response_text.strip()
        
        # Try to parse the JSON response
        try:
            questions_data = json.loads(response_text)
            
            # Validate the response structure
            if "questions" not in questions_data or not isinstance(questions_data["questions"], list):
                raise ValueError("Invalid response structure")
            
            # Add metadata
            result = {
                "article_url": url,
                "article_index": article_index,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "questions": questions_data["questions"],
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            print(f"✅ Generated {len(questions_data['questions'])} questions for article {article_index + 1}")
            return result
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response for article {article_index + 1}: {e}")
            print(f"Response was: {response_text[:200]}...")
            return None
            
    except Exception as e:
        print(f"❌ Error generating questions for article {article_index + 1}: {e}")
        return None

def save_questions_incrementally(questions: List[Dict[str, Any]], output_file: str):
    """Save questions to file incrementally"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_articles_processed": len(questions),
                "evaluation_questions": questions
            }, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(questions)} question sets to {output_file}")
    except Exception as e:
        print(f"❌ Error saving questions: {e}")

def main():
    """Main function to generate evaluation questions"""
    
    # Configuration
    teamdynamix_file = "/home/exouser/AI-Agent-Askus/web-scraper/data/kb_articles_extracted.json"
    output_file = "/home/exouser/AI-Agent-Askus/evaluation/evaluation_questions.json"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print("🚀 Starting TeamDynamix Evaluation Question Generation")
    print(f"📁 Using data from: {teamdynamix_file}")
    print("=" * 60)
    
    # Initialize OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    
    # Load TeamDynamix data
    articles = load_teamdynamix_data(teamdynamix_file)
    if not articles:
        print("❌ No articles loaded, exiting")
        sys.exit(1)
    
    # Generate questions
    all_questions = []
    processed_count = 0
    
    print(f"Processing all {len(articles)} articles...")
    
    for i, article in enumerate(articles):
        try:
            questions = generate_questions_for_article(client, article, i)
            
            if questions:
                all_questions.append(questions)
                processed_count += 1
                
                # Save incrementally every 10 articles
                if processed_count % 10 == 0:
                    save_questions_incrementally(all_questions, output_file)
                    print(f"📊 Progress: {processed_count}/{len(articles)} articles processed")
            
            # Rate limiting - wait between requests
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\n⏹️  Process interrupted by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error processing article {i + 1}: {e}")
            continue
    
    # Final save
    save_questions_incrementally(all_questions, output_file)
    
    print("\n" + "=" * 60)
    print("✅ Question Generation Complete!")
    print(f"📊 Total articles processed: {processed_count}/{len(articles)}")
    print(f"📝 Total question sets generated: {len(all_questions)}")
    print(f"💾 Output saved to: {output_file}")
    
    # Calculate total questions
    total_questions = sum(len(q.get('questions', [])) for q in all_questions)
    print(f"❓ Total individual questions: {total_questions}")

if __name__ == "__main__":
    main()
