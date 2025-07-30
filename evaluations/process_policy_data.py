#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to process the policy documents and generated questions:
- Extract document text from JSON files
- Chunk text with configurable chunk size and overlap
- Format the generated questions
- Output chunked datasets and metadata to /data in the format required by create_vector_db.py
"""

import os
import json
from typing import Dict, List, Tuple, Any, Optional
import argparse
from bs4 import BeautifulSoup
import re
import html
from pathlib import Path
import uuid

class PolicyDocumentProcessor:
    def __init__(self, 
                 policies_path: str, 
                 questions_path: str, 
                 output_dir: str, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200,
                 dataset_name: str = "policy_eval"):
        """
        Initialize the policy document processor.
        
        Args:
            policies_path: Path to the JSON file containing policy documents
            questions_path: Path to the JSON file containing generated questions
            output_dir: Directory to output the processed data
            chunk_size: Size of each text chunk
            chunk_overlap: Overlap between chunks
            dataset_name: Name prefix for the dataset files
        """
        self.policies_path = policies_path
        self.questions_path = questions_path
        self.output_dir = output_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.dataset_name = dataset_name
        
        # Create output directory structure if it doesn't exist
        self.chunks_dir = os.path.join(output_dir, "chunks")
        self.questions_dir = os.path.join(output_dir, "questions")
        os.makedirs(self.chunks_dir, exist_ok=True)
        os.makedirs(self.questions_dir, exist_ok=True)
        
    def clean_policy_text(self, text: str) -> str:
        """
        Clean and format policy text.
        
        Args:
            text: Raw policy text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Optional: remove common formatting markers
        # This can be customized based on the policy document format
        text = re.sub(r'#{1,6}\s+', '', text)  # Remove markdown headers
        
        return text

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

    def process_policies(self) -> List[Dict[str, Any]]:
        """
        Load and process policy documents from JSON file.
        
        Returns:
            List of processed policy documents
        """
        with open(self.policies_path, 'r') as f:
            policies = json.load(f)
            
        processed_policies = []
        for policy in policies:
            doc_url = policy.get("url", "")
            doc_id = doc_url.split('/')[-1] if doc_url else f"doc_{uuid.uuid4()}"
            
            # Extract document title from URL or text
            title_match = re.search(r'policyNumber=(\w+)', doc_url)
            title = f"Policy {title_match.group(1)}" if title_match else doc_id
            
            processed_policies.append({
                "id": doc_id,
                "title": title,
                "url": doc_url,
                "text": policy.get("extracted", ""),
                "source": "policy"
            })
            
        return processed_policies
        
    def _process_policy_batch(self, policy_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of policy documents and create chunks.
        
        Args:
            policy_batch: A batch of policies to process
            
        Returns:
            List of chunked documents from this batch
        """
        chunked_documents = []
        
        for policy in policy_batch:
            # Process each policy in the batch
            doc_url = policy.get("url", "")
            doc_id = doc_url.split('/')[-1] if doc_url else f"doc_{uuid.uuid4()}"
            
            # Extract document title from URL or text
            title_match = re.search(r'policyNumber=(\w+)', doc_url)
            title = f"Policy {title_match.group(1)}" if title_match else doc_id
            
            # Clean text if needed
            text = self.clean_policy_text(policy.get("extracted", ""))
            
            # Chunk the text
            chunks = self.chunk_text(text, self.chunk_size, self.chunk_overlap)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunked_documents.append({
                    "id": chunk_id,
                    "chunk_id": i,
                    "document_id": doc_id,
                    "document_title": title,
                    "document_url": doc_url,
                    "text": chunk,
                    "source": "policy"
                })
                
        return chunked_documents

    def load_questions(self) -> List[Dict[str, Any]]:
        """
        Load generated questions from JSON file.
        
        Returns:
            List of questions
        """
        with open(self.questions_path, 'r') as f:
            questions = json.load(f)
            
        return questions

    def process_data(self) -> Tuple[str, str]:
        """
        Process the policy documents and questions.
        
        Returns:
            Tuple of (chunk_file_path, questions_file_path)
        """
        # Create a dataset ID based on parameters
        dataset_id = f"{self.dataset_name}_{self.chunk_size}_{self.chunk_overlap}"
        chunks_file = os.path.join(self.chunks_dir, f"{dataset_id}.json")
        questions_file = os.path.join(self.questions_dir, f"{dataset_id}_questions.json")
        
        # Initialize files with empty arrays
        with open(chunks_file, 'w') as f:
            f.write('[\n')
            
        # Process documents in batches
        print(f"Processing policy documents from {self.policies_path}")
        with open(self.policies_path, 'r') as f:
            policies = json.load(f)
        
        print(f"Loaded {len(policies)} policy documents")
        
        # Process in batches to reduce memory usage
        batch_size = 10
        total_chunks = 0
        doc_ids = set()
        
        for batch_idx in range(0, len(policies), batch_size):
            batch = policies[batch_idx:batch_idx + batch_size]
            processed_batch = self._process_policy_batch(batch)
            
            # Write chunks to file incrementally
            with open(chunks_file, 'a') as f:
                for i, chunk_doc in enumerate(processed_batch):
                    doc_ids.add(chunk_doc["document_id"])
                    if total_chunks > 0 or i > 0:
                        f.write(',\n')
                    json.dump(chunk_doc, f)
                    total_chunks += 1
            
            print(f"Processed batch {batch_idx//batch_size + 1}/{(len(policies)-1)//batch_size + 1} - {total_chunks} total chunks")
        
        # Close the chunks JSON array
        with open(chunks_file, 'a') as f:
            f.write('\n]')
            
        print(f"Created {total_chunks} chunks from {len(doc_ids)} documents")
        
        # Process questions
        print(f"Loading questions from {self.questions_path}")
        questions = self.load_questions()
        
        # Format and save questions
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                "id": q["id"],
                "question": q["question"],
                "document_id": q["document_id"],
                "document_url": q.get("document_url", ""),
                "answer_clean_html": "",  # We don't have answers, so leave empty
                "answer_html": "",  # We don't have answers, so leave empty
                "answer_text": ""   # Required by create_vector_db.py for evaluation
            })
        
        # Save questions
        with open(questions_file, 'w') as f:
            json.dump(formatted_questions, f, indent=2)
            
        print(f"Saved {len(formatted_questions)} questions to {questions_file}")
        
        # Save dataset info
        info = {
            "dataset_id": dataset_id,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "num_documents": len(doc_ids),
            "num_chunks": total_chunks,
            "num_questions": len(formatted_questions)
        }
        
        info_file = os.path.join(self.output_dir, f"{dataset_id}_info.json")
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
            
        print(f"Saved dataset info to: {info_file}")
        
        return chunks_file, questions_file

    def save_output(self, chunks_file_path: str, questions_file_path: str):
        """
        Prints information about the saved data.
        
        Args:
            chunks_file_path: Path to the saved chunks file
            questions_file_path: Path to the saved questions file
        """
        print(f"Saved chunked documents to: {chunks_file_path}")
        print(f"Saved questions to: {questions_file_path}")
        
        # Dataset info is already saved in process_data

def main():
    parser = argparse.ArgumentParser(description='Process policy documents and questions for RAG evaluation')
    parser.add_argument('--policies_path', type=str, default='testing/policies.json',
                        help='Path to the JSON file containing policy documents')
    parser.add_argument('--questions_path', type=str, default='data/evaluation_questions.json',
                        help='Path to the JSON file containing generated questions')
    parser.add_argument('--output_dir', type=str, default='data',
                        help='Directory to output the processed data')
    parser.add_argument('--chunk_size', type=int, default=1000,
                        help='Size of each text chunk')
    parser.add_argument('--chunk_overlap', type=int, default=200,
                        help='Overlap between chunks')
    parser.add_argument('--dataset_name', type=str, default='policy_eval',
                        help='Name prefix for the dataset files')
    parser.add_argument('--batch_size', type=int, default=10,
                        help='Number of documents to process in each batch')
    
    args = parser.parse_args()
    
    # Create the document processor
    processor = PolicyDocumentProcessor(
        policies_path=args.policies_path,
        questions_path=args.questions_path,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        dataset_name=args.dataset_name
    )
    
    # Process the data - now returns file paths instead of data
    chunks_file, questions_file = processor.process_data()
    
    # Report on the saved output
    processor.save_output(chunks_file, questions_file)
    
    print("Data processing complete.")
    print(f"Try running with a smaller chunk size if you encounter memory issues.")
    print(f"Current chunk_size: {args.chunk_size}, chunk_overlap: {args.chunk_overlap}")
    print(f"Recommended chunk_size for large documents: 200-500")


if __name__ == "__main__":
    main()
