#!/usr/bin/env python3

import os
import glob
import json
import re
from bs4 import BeautifulSoup

def clean_text(text):
    """
    Clean the text by removing extra whitespace, blank lines, and special characters
    """
    # Replace multiple spaces, newlines, and tabs with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text

def parse_askus_html_file(file_path):
    """
    Parse an AskUs HTML file and extract:
    1. Title text
    2. Clean document content between kb_article_question and kb_article_footer
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title_tag = soup.find('title')
        title_text = ""
        if title_tag:
            # Clean up the title (remove any :: ASK US, University of Hawaii System, etc.)
            title_text = title_tag.get_text().strip()
            title_text = re.sub(r'\s+::\s+ASK US.*$', '', title_text)
            title_text = re.sub(r'\n+', ' ', title_text).strip()
        
        # Find content between kb_article_question and kb_article_footer
        start_elem = soup.find(id="kb_article_question")
        
        # If kb_article_footer doesn't exist, we'll capture until the end of kb_article_text
        end_elem = soup.find(id="kb_article_footer")
        if not end_elem:
            # Use the kb_article_text as our container if available
            container = soup.find(id="kb_article_text")
            document_text = ""
            if container:
                document_text = container.get_text(strip=True)
        else:
            # Extract all content between start and end elements
            document_text = ""
            if start_elem:
                # Start from the element after kb_article_question
                current = start_elem.next_sibling
                while current and current != end_elem:
                    if hasattr(current, 'get_text'):
                        document_text += current.get_text() + " "
                    current = current.next_sibling
        
        # Clean the document text
        document_text = clean_text(document_text)
        
        return {
            "text": title_text,  # Title becomes the main text for embedding
            "metadata": {
                "document": document_text,  # Clean document text as metadata
            }
        }
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def parse_all_askus_files(directory='.'):
    """
    Parse all HTML files in the specified directory and return an array of results
    """
    results = []
    
    # Find all HTML files in the directory
    html_files = glob.glob(os.path.join(directory, '*.html'))
    
    for file_path in html_files:
        result = parse_askus_html_file(file_path)
        if result:
            results.append(result)
    
    return results

if __name__ == "__main__":
    # Parse all HTML files in the current directory
    directory = os.path.dirname(os.path.abspath(__file__))
    results = parse_all_askus_files(directory)
    
    # Print some statistics
    print(f"Processed {len(results)} files")
    
    # Write results to a JSON file
    output_file = os.path.join(directory, 'parsed_askus_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results written to {output_file}")
    
    # Print a sample of the first result if available
    if results:
        print("\nSample of first result:")
        print(f"Text: {results[0]['text'][:100]}...")
        print(f"Document: {results[0]['metadata']['document'][:100]}...")
