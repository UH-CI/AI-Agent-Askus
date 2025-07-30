#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to process the Natural Questions dataset:
- Extract document text from JSONL
- Chunk text with configurable chunk size and overlap
- Optionally remove HTML
- Extract questions with clean and non-clean answers
- Output chunked datasets and metadata to /data
"""

import os
import json
import jsonlines
from typing import Dict, List, Tuple, Any, Optional
import argparse
from bs4 import BeautifulSoup
import re
import html
import numpy as np
import base64
from pathlib import Path
import uuid

def clean_wikipedia_html(html_string: str) -> str:
    """Clean and extract text content from Wikipedia HTML."""
    soup = BeautifulSoup(html_string, 'html.parser')

    # Remove all non-visible or irrelevant tags
    for tag in soup(['script', 'style', 'head', 'meta', 'noscript', 'link']):
        tag.decompose()

    # Target only main article content
    content_div = soup.find('div', id='mw-content-text')
    if content_div:
        text = content_div.get_text(separator=' ')
    else:
        text = soup.get_text(separator=' ')

    # Unescape HTML entities (e.g., &nbsp;)
    text = html.unescape(text)

    # Replace all types of whitespace (including unicode ones) with single spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Optional: remove common Wikipedia junk phrases
    junk_phrases = ['Jump to:', 'navigation', 'search', 'From Wikipedia, the free encyclopedia']
    for phrase in junk_phrases:
        text = text.replace(phrase, '')

    return text.strip()

class DocumentProcessor:
    def __init__(self, jsonl_path: str, output_dir: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the document processor.
        
        Args:
            jsonl_path: Path to the JSONL file containing the NQ dataset
            output_dir: Directory to output the processed data
            chunk_size: Size of each text chunk
            chunk_overlap: Overlap between chunks
        """
        self.jsonl_path = jsonl_path
        self.output_dir = output_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create output directory structure if it doesn't exist
        self.chunks_dir = os.path.join(output_dir, "chunks")
        self.questions_dir = os.path.join(output_dir, "questions")
        os.makedirs(self.chunks_dir, exist_ok=True)
        os.makedirs(self.questions_dir, exist_ok=True)
        
    def chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Split a text into chunks of specified size with overlap.
        
        Args:
            text: The text to chunk
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Simple implementation of sliding window chunking
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to find a clean break at a sentence or paragraph
            if end < len(text):
                for separator in ['. ', '! ', '? ', '\n\n', '\n', ' ']:
                    break_point = text.rfind(separator, start + chunk_size // 2, end)
                    if break_point != -1:
                        end = break_point + len(separator)
                        break
            
            # Add the chunk
            chunks.append(text[start:end])
            
            # Move start point for the next chunk, considering overlap
            start = end - chunk_overlap
            
            # Ensure we're making progress
            if start >= len(text) - 1:
                break
            
            # Avoid tiny final chunks
            if len(text) - start < chunk_size // 2:
                chunks[-1] = chunks[-1] + " " + text[start:]
                break
                
        return chunks

    def extract_documents(self, remove_html: bool = True) -> List[Dict[str, Any]]:
        """
        Extract document text from the JSONL file.
        
        Args:
            remove_html: Whether to remove HTML from document text
            
        Returns:
            List of documents with their text and metadata
        """
        documents = []
        
        with jsonlines.open(self.jsonl_path) as reader:
            for idx, obj in enumerate(reader):
                if "document_html" not in obj:
                    continue
                
                document_id = obj.get("example_id", f"doc_{idx}")
                document_title = obj.get("document_title", "")
                document_url = obj.get("document_url", "")
                
                # Process the document text based on whether to remove HTML or not
                if remove_html:
                    document_text = clean_wikipedia_html(obj["document_html"])
                else:
                    document_text = obj["document_html"]
                
                documents.append({
                    "id": document_id,
                    "title": document_title,
                    "url": document_url,
                    "text": document_text,
                    "source": "v1.0_sample_nq"
                })
                
        return documents

    def extract_questions_and_answers(self) -> List[Dict[str, Any]]:
        """
        Extract questions and answers from the JSONL file.
        
        Returns:
            List of questions with their clean and non-clean answers
        """
        questions = []
        
        with jsonlines.open(self.jsonl_path) as reader:
            for idx, obj in enumerate(reader):
                if "question_text" not in obj or "annotations" not in obj:
                    continue
                
                question_id = obj.get("example_id", f"q_{idx}")
                question_text = obj["question_text"]
                
                # Extract answers
                has_answer = False
                
                # Check if annotations has long_answer with valid start_byte
                long_answers = [
                    a["long_answer"]
                    for a in obj["annotations"]
                    if a.get("long_answer", {}).get("start_byte", -1) >= 0
                ]
                
                if long_answers:
                    has_answer = True
                    
                    # Get the most common answer span
                    long_answer_bounds = [
                        (la["start_byte"], la["end_byte"]) for la in long_answers
                    ]
                    
                    long_answer_counts = [
                        long_answer_bounds.count(la) for la in long_answer_bounds
                    ]
                    
                    # Get the most common answer
                    if long_answer_counts:
                        most_common_idx = np.argmax(long_answer_counts)
                        long_answer = long_answers[most_common_idx]
                        
                        # Extract the answer text
                        answer_html = obj["document_html"][long_answer["start_byte"]:long_answer["end_byte"]]
                        clean_answer = clean_wikipedia_html(answer_html)
                        
                        questions.append({
                            "id": question_id,
                            "question": question_text,
                            "answer_html": answer_html,
                            "answer_text": clean_answer,
                            "document_id": obj.get("example_id", f"doc_{idx}"),
                            "document_url": obj.get("document_url", "")
                        })
                
        return questions

    def process_data(self, remove_html: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process the data by extracting documents, chunking them, and extracting questions.
        
        Args:
            remove_html: Whether to remove HTML from document text
            
        Returns:
            Tuple of (chunked documents, questions)
        """
        # Extract documents
        print(f"Extracting documents from {self.jsonl_path}...")
        documents = self.extract_documents(remove_html)
        print(f"Extracted {len(documents)} documents.")
        
        # Chunk documents
        print(f"Chunking documents with chunk size {self.chunk_size} and overlap {self.chunk_overlap}...")
        chunked_documents = []
        
        for doc in documents:
            chunks = self.chunk_text(doc["text"], self.chunk_size, self.chunk_overlap)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc['id']}_chunk_{i}"
                chunked_documents.append({
                    "id": chunk_id,
                    "chunk_id": i,
                    "document_id": doc["id"],
                    "document_title": doc["title"],
                    "document_url": doc["url"],
                    "text": chunk,
                    "source": doc["source"]
                })
                
        print(f"Created {len(chunked_documents)} chunks from {len(documents)} documents.")
        
        # Extract questions and answers
        print("Extracting questions and answers...")
        questions = self.extract_questions_and_answers()
        print(f"Extracted {len(questions)} questions.")
        
        return chunked_documents, questions

    def save_output(self, chunked_documents: List[Dict[str, Any]], questions: List[Dict[str, Any]], remove_html: bool = True):
        """
        Save the processed data to output files.
        
        Args:
            chunked_documents: List of chunked documents
            questions: List of questions with answers
            remove_html: Whether HTML was removed (for naming output files)
        """
        # Create a dataset ID based on parameters
        dataset_id = f"nq_chunks_{self.chunk_size}_{self.chunk_overlap}_{'clean' if remove_html else 'html'}"
        
        # Save chunked documents
        chunks_file = os.path.join(self.chunks_dir, f"{dataset_id}.json")
        with open(chunks_file, 'w') as f:
            json.dump(chunked_documents, f, indent=2)
        
        # Save questions and answers
        questions_file = os.path.join(self.questions_dir, f"{dataset_id}_questions.json")
        with open(questions_file, 'w') as f:
            json.dump(questions, f, indent=2)
            
        print(f"Saved chunked documents to: {chunks_file}")
        print(f"Saved questions and answers to: {questions_file}")
        
        # Save a dataset info file
        info = {
            "dataset_id": dataset_id,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "remove_html": remove_html,
            "num_documents": len(set(d["document_id"] for d in chunked_documents)),
            "num_chunks": len(chunked_documents),
            "num_questions": len(questions)
        }
        
        info_file = os.path.join(self.output_dir, f"{dataset_id}_info.json")
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
            
        print(f"Saved dataset info to: {info_file}")

def main():
    parser = argparse.ArgumentParser(description='Process Natural Questions dataset for RAG evaluation')
    parser.add_argument('--jsonl_path', type=str, default='v1.0_sample_nq-dev-sample.jsonl',
                        help='Path to the JSONL file containing the NQ dataset')
    parser.add_argument('--output_dir', type=str, default='data',
                        help='Directory to output the processed data')
    parser.add_argument('--chunk_size', type=int, default=1000,
                        help='Size of each text chunk')
    parser.add_argument('--chunk_overlap', type=int, default=200,
                        help='Overlap between chunks')
    parser.add_argument('--keep_html', action='store_true',
                        help='Keep HTML in document text (default: remove HTML)')
    
    args = parser.parse_args()
    
    # Create the document processor
    processor = DocumentProcessor(
        jsonl_path=args.jsonl_path,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    # Process the data
    chunked_documents, questions = processor.process_data(remove_html=not args.keep_html)
    
    # Save the output
    processor.save_output(chunked_documents, questions, remove_html=not args.keep_html)
    
    print("Data processing complete.")

if __name__ == "__main__":
    main()
