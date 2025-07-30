#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to generate evaluation questions for policy documents using Google's Gemini AI.

This script reads policy documents from a JSON file, sends each document's text to 
Gemini AI, and requests it to generate relevant questions. The generated questions
are saved with document IDs to a new JSON file for RAG evaluation.
"""

import os
import json
import uuid
import argparse
from typing import List, Dict, Any
import google.generativeai as genai
from pathlib import Path
import time

class QuestionGenerator:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize the question generator with Google API credentials.
        
        Args:
            api_key: Google API key for Gemini
            model_name: Name of the Gemini model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
    def load_documents(self, json_path: str) -> List[Dict[str, Any]]:
        """
        Load policy documents from a JSON file.
        
        Args:
            json_path: Path to the JSON file containing policy documents
            
        Returns:
            List of document dictionaries
        """
        with open(json_path, 'r') as f:
            documents = json.load(f)
        
        print(f"Loaded {len(documents)} documents from {json_path}")
        return documents
    
    def generate_answer(self, question: str, doc_text: str) -> str:
        """
        Generate a gold-standard answer for a question based strictly on the document content.
        
        Args:
            question: The question to answer
            doc_text: The document text to base the answer on
            
        Returns:
            The generated answer based only on the document
        """
        prompt = f"""
        You are tasked with answering a question based STRICTLY on the provided document. 
        
        IMPORTANT RULES:
        1. Only use information that is explicitly stated in the document
        2. Do not add any external knowledge or make assumptions
        3. If the document doesn't contain enough information to answer the question, say "The document does not provide sufficient information to answer this question."
        4. Quote relevant parts of the document when possible
        5. Keep your answer concise and directly relevant to the question
        
        Question: {question}
        
        Document:
        {doc_text}
        
        Answer based strictly on the document:
        """
        
        try:
            response = self.model.generate_content(prompt)
            answer = response.text.strip()
            return answer
        except Exception as e:
            print(f"Error generating answer: {e}")
            return "Error generating answer from document."
    
    def generate_questions_and_answers(self, document: Dict[str, Any], num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Generate questions and their corresponding gold-standard answers for a given document using Gemini AI.
        
        Args:
            document: Document dictionary with text content
            num_questions: Number of questions to generate per document
            
        Returns:
            List of question dictionaries with question text, answers, and metadata
        """
        doc_text = document.get("extracted", "")
        doc_url = document.get("url", "")
        
        if not doc_text:
            print("No document text found, skipping...")
            return []
        
        # Create a document ID from the URL or generate a random one
        doc_id = f"doc_{uuid.uuid4()}"
        
        # Prepare the prompt for Gemini
        prompt = f"""
        I'll provide you with a document on answers to policy data. Please generate {num_questions} diverse questions that could be answered using this document. 
        The questions should:
        1. Cover different parts of the document
        2. Range from simple factual questions to more complex interpretative questions
        3. Be specific enough that they can be answered directly from the document
        4. Be formulated as complete questions (ending with a question mark)

        Return ONLY a numbered list of questions, nothing else.

        Here's the document:
        {doc_text}
        """
        
        try:
            # Generate questions using Gemini
            response = self.model.generate_content(prompt)
            generated_text = response.text.strip()
            
            # Parse the numbered list of questions
            questions_raw = [q.strip() for q in generated_text.split('\n') if q.strip()]
            
            # Clean up the questions (remove numbering and leading/trailing whitespace)
            cleaned_questions = []
            for q in questions_raw:
                # Remove numbering (e.g., "1.", "2.", etc.)
                if '. ' in q and q[0].isdigit():
                    q = q.split('. ', 1)[1].strip()
                cleaned_questions.append(q)
            
            # Create question dictionaries with answers
            questions = []
            for i, q_text in enumerate(cleaned_questions):
                if q_text and '?' in q_text:  # Ensure it's an actual question
                    # Generate gold-standard answer for this question
                    print(f"Generating answer for question {i+1}: {q_text[:50]}...")
                    answer = self.generate_answer(q_text, doc_text)
                    
                    questions.append({
                        "id": f"{doc_id}_q{i+1}",
                        "question": q_text,
                        "answer": answer,
                        "document_id": doc_id,
                        "document_url": doc_url,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Small delay between answer generations to avoid rate limits
                    time.sleep(0.5)
            
            print(f"Generated {len(questions)} questions with answers for document {doc_id}")
            return questions
            
        except Exception as e:
            print(f"Error generating questions for document {doc_id}: {e}")
            return []
    
    def generate_questions(self, document: Dict[str, Any], num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Legacy method - now calls generate_questions_and_answers for backward compatibility.
        
        Args:
            document: Document dictionary with text content
            num_questions: Number of questions to generate per document
            
        Returns:
            List of question dictionaries with question text and metadata
        """
        return self.generate_questions_and_answers(document, num_questions)
    
    def process_documents(self, documents: List[Dict[str, Any]], num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Process all documents and generate questions for each.
        
        Args:
            documents: List of document dictionaries
            num_questions: Number of questions to generate per document
            
        Returns:
            List of question dictionaries for all documents
        """
        all_questions = []
        
        for i, doc in enumerate(documents):
            print(f"Processing document {i+1}/{len(documents)}...")
            questions = self.generate_questions(doc, num_questions)
            all_questions.extend(questions)
            
            # Add a small delay to avoid hitting API rate limits
            if i < len(documents) - 1:
                time.sleep(1)
        
        return all_questions
    
    def save_questions(self, questions: List[Dict[str, Any]], output_path: str):
        """
        Save generated questions to a JSON file.
        
        Args:
            questions: List of question dictionaries
            output_path: Path to save the questions JSON file
        """
        with open(output_path, 'w') as f:
            json.dump(questions, f, indent=2)
        
        print(f"Saved {len(questions)} questions to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate evaluation questions from policy documents using Gemini')
    
    parser.add_argument('--input', type=str, default='data/documents/policies.json',
                        help='Path to the input JSON file containing policy documents')
    
    parser.add_argument('--output', type=str, default='data/evaluation_questions2.json',
                        help='Path to save the generated questions')
    
    parser.add_argument('--api_key', type=str, required=True,
                        help='Google API key for accessing Gemini')
    
    parser.add_argument('--num_questions', type=int, default=5,
                        help='Number of questions to generate per document')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Initialize the question generator
    generator = QuestionGenerator(api_key=args.api_key)
    
    # Load documents
    documents = generator.load_documents(args.input)
    
    # Generate questions
    questions = generator.process_documents(documents, args.num_questions)
    
    # Save questions
    generator.save_questions(questions, args.output)
    
    print(f"Question generation complete. Generated {len(questions)} total questions across {len(documents)} documents.")

if __name__ == "__main__":
    main()
