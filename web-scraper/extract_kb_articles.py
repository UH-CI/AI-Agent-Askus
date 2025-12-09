#!/usr/bin/env python3
"""
Extract body and URL from TeamDynamix Knowledge Base articles
and format them like policies.json and urls.json
"""

import json
import os
from html import unescape
import re
import html2text

def convert_html_to_markdown(html_content):
    """
    Convert HTML content to markdown format to match policies.json/urls.json
    Uses html2text library like the original policy_spider.py
    """
    if not html_content:
        return ""
    
    # Create html2text converter (same as policy_spider.py)
    h = html2text.HTML2Text()
    h.ignore_links = False  # Keep links (different from policy_spider which ignores them)
    h.ignore_images = True  # Ignore images
    h.body_width = 0  # Don't wrap lines
    h.unicode_snob = True  # Use unicode
    
    # Convert HTML to markdown
    markdown_content = h.handle(html_content)
    
    # Clean up the markdown
    # Remove excessive newlines
    markdown_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', markdown_content)
    
    # Clean up any remaining \r\n
    markdown_content = markdown_content.replace('\r\n', '\n')
    
    # Remove trailing whitespace from lines
    lines = markdown_content.split('\n')
    cleaned_lines = [line.rstrip() for line in lines]
    markdown_content = '\n'.join(cleaned_lines)
    
    return markdown_content.strip()

def construct_article_url(article):
    """
    Construct a URL for the knowledge base article
    Based on the URI pattern and article information
    """
    # The URI field contains something like "api/277/knowledgebase/3728"
    # We need to construct a proper TeamDynamix URL
    
    app_id = article.get('AppID', '')
    article_id = article.get('ID', '')
    
    # TeamDynamix knowledge base URL pattern
    base_url = "https://solutions.teamdynamix.com"
    
    if app_id and article_id:
        # Construct URL based on the pattern observed in the API
        url = f"{base_url}/TDClient/{app_id}/Portal/KB/ArticleDet?ID={article_id}"
        return url
    
    # Fallback to a generic URL if we can't construct the specific one
    return f"{base_url}/TDClient/Portal/KB/ArticleDet?ID={article_id}"

def extract_kb_articles(input_file, output_file):
    """
    Extract knowledge base articles and format them like policies.json/urls.json
    """
    print(f"Reading knowledge base articles from: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {input_file} not found")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_file}: {e}")
        return False
    
    # Extract detailed articles
    detailed_articles = kb_data.get('detailed_articles', [])
    
    if not detailed_articles:
        print("No detailed articles found in the input file")
        return False
    
    print(f"Found {len(detailed_articles)} detailed articles")
    
    # Process articles and create the output format
    extracted_articles = []
    successful_count = 0
    
    for article_data in detailed_articles:
        status = article_data.get('status', '')
        
        if status == 'success':
            article = article_data.get('article', {})
            
            if article:
                # Extract the body content
                body = article.get('Body', '')
                subject = article.get('Subject', '')
                
                # Convert HTML to markdown
                markdown_body = convert_html_to_markdown(body)
                
                # Construct the URL
                url = construct_article_url(article)
                
                # Create the output object in the same format as policies.json/urls.json
                article_obj = {
                    "url": url,
                    "extracted": markdown_body
                }
                
                extracted_articles.append(article_obj)
                successful_count += 1
                
                print(f"Processed article: {subject} (ID: {article.get('ID', 'Unknown')})")
        else:
            # Log failed articles
            article_id = article_data.get('article_id', 'Unknown')
            error = article_data.get('error', 'Unknown error')
            print(f"Skipped article {article_id} with status '{status}': {error}")
    
    print(f"\nSuccessfully processed {successful_count} articles")
    
    # Save the extracted articles
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_articles, f, indent=2, ensure_ascii=False)
        
        print(f"Extracted articles saved to: {output_file}")
        print(f"Output file size: {os.path.getsize(output_file)} bytes")
        
        return True
        
    except Exception as e:
        print(f"Error saving output file: {e}")
        return False

def main():
    """
    Main function to extract KB articles
    """
    # File paths
    input_file = '/home/exouser/AI-Agent-Askus/web-scraper/data/kb_articles_results.json'
    output_file = '/home/exouser/AI-Agent-Askus/web-scraper/data/kb_articles_extracted.json'
    
    print("TeamDynamix Knowledge Base Articles Extractor")
    print("=" * 50)
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist")
        return
    
    # Extract the articles
    success = extract_kb_articles(input_file, output_file)
    
    if success:
        print("\n✅ Extraction completed successfully!")
        print(f"📁 Output saved to: {output_file}")
        
        # Show some statistics
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                extracted_data = json.load(f)
            print(f"📊 Total articles extracted: {len(extracted_data)}")
        except Exception as e:
            print(f"Warning: Could not read output file for statistics: {e}")
    else:
        print("\n❌ Extraction failed!")

if __name__ == "__main__":
    main()
