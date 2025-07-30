#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to create a ChromaDB vector database from chunked documents
and evaluate retrieval performance against gold standard answers.
"""

import os
import json
import argparse
from typing import Dict, List, Any, Optional, Tuple
import chromadb
from chromadb.utils import embedding_functions
import tiktoken
import time
import numpy as np
from pathlib import Path
import uuid

class VectorDatabaseCreator:
    def __init__(self, data_dir: str, db_dir: str):
        """
        Initialize the vector database creator.
        
        Args:
            data_dir: Directory containing the processed data
            db_dir: Directory to store the ChromaDB database
        """
        self.data_dir = data_dir
        self.db_dir = db_dir
        self.chunks_dir = os.path.join(data_dir, "chunks")
        self.questions_dir = os.path.join(data_dir, "questions")
        
        # Create output directory if it doesn't exist
        os.makedirs(db_dir, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=db_dir)
        
        # Use default OpenAI embedding function (text-embedding-ada-002)
        # Note: This can be replaced with any embedding function compatible with ChromaDB
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

    def load_dataset(self, dataset_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Load a processed dataset.
        
        Args:
            dataset_id: ID of the dataset to load
            
        Returns:
            Tuple of (chunked documents, questions)
        """
        # Load chunked documents
        chunks_file = os.path.join(self.chunks_dir, f"{dataset_id}.json")
        with open(chunks_file, 'r') as f:
            chunked_documents = json.load(f)
            
        # Load questions
        questions_file = os.path.join(self.questions_dir, f"{dataset_id}_questions.json")
        with open(questions_file, 'r') as f:
            questions = json.load(f)
            
        return chunked_documents, questions

    def create_collection(self, dataset_id: str, chunked_documents: List[Dict[str, Any]], k: int = None) -> chromadb.Collection:
        """
        Create a ChromaDB collection for the dataset.
        
        Args:
            dataset_id: ID of the dataset
            chunked_documents: List of chunked documents
            k: Optional parameter to create unique collection name for parallel runs
            
        Returns:
            The created ChromaDB collection
        """
        # Create a unique collection name if k is provided
        collection_name = f"{dataset_id}_k{k}" if k is not None else dataset_id
        
        # Check if collection already exists
        try:
            collection = self.client.get_collection(name=collection_name)
            print(f"Collection already exists: {collection_name}, reusing it")
            return collection
        except Exception:
            # Collection doesn't exist, create it
            pass
        
        # Create a new collection
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={
                "description": f"Chunked documents from {dataset_id}",
                "k": k if k is not None else "default"
            }
        )
        print(f"Created new collection with name: {collection_name}")
        
        # Verify the collection exists before adding documents
        try:
            collection = self.client.get_collection(name=collection_name)
            print(f"Successfully verified collection exists: {collection_name}")
        except Exception as e:
            print(f"Error verifying collection: {e}")
            raise
        
        # Prepare data for batch insertion
        ids = []
        documents = []
        metadatas = []
        
        for doc in chunked_documents:
            ids.append(doc["id"])
            documents.append(doc["text"])
            
            # Prepare metadata (exclude text field to avoid duplication)
            metadata = {k: v for k, v in doc.items() if k != "text"}
            metadatas.append(metadata)
        
        # Add documents in batches to avoid memory issues
        batch_size = 1000
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_documents = documents[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            try:
                collection.add(
                    ids=batch_ids,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                print(f"Added {len(batch_ids)} documents to collection (batch {i//batch_size + 1})")
            except Exception as e:
                print(f"Error adding documents to collection: {e}")
                raise
        
        return collection

    def evaluate_retrieval(self, collection: chromadb.Collection, questions: List[Dict[str, Any]], k: int = 2) -> Dict[str, Any]:
        """
        Evaluate retrieval performance against gold standard answers.
        
        Args:
            collection: ChromaDB collection to query
            questions: List of questions with gold standard answers
            k: Number of documents to retrieve
            
        Returns:
            Dictionary of evaluation results
        """
        results = []
        correct_retrievals = 0
        
        for idx, question in enumerate(questions):
            # Query the collection with the question text
            query_result = collection.query(
                query_texts=[question["question"]],
                n_results=k
            )
            
            # Get the retrieved document IDs
            retrieved_ids = query_result["ids"][0]
            retrieved_docs = query_result["documents"][0]
            retrieved_metadatas = query_result["metadatas"][0]
            retrieved_distances = query_result["distances"][0] if "distances" in query_result else None
            
            # Check if any of the retrieved documents are from the same document as the gold answer
            gold_document_id = question["document_id"]
            retrieved_document_ids = [metadata.get("document_id") for metadata in retrieved_metadatas]
            
            # Check if the gold document was retrieved
            correct_retrieval = gold_document_id in retrieved_document_ids
            if correct_retrieval:
                correct_retrievals += 1
                
            # Add result for this question
            results.append({
                "question_id": question["id"],
                "question": question["question"],
                "gold_document_id": gold_document_id,
                "retrieved_document_ids": retrieved_document_ids,
                "correct_retrieval": correct_retrieval,
                "retrieved_chunks": [
                    {
                        "id": retrieved_ids[i],
                        "text": retrieved_docs[i][:200] + "..." if len(retrieved_docs[i]) > 200 else retrieved_docs[i],
                        "metadata": retrieved_metadatas[i],
                        "distance": retrieved_distances[i] if retrieved_distances else None
                    }
                    for i in range(len(retrieved_ids))
                ],
                "gold_answer_html": question["answer_html"],
                "gold_answer_text": question["answer_text"]
            })
            
            # Print progress
            if (idx + 1) % 10 == 0:
                print(f"Processed {idx + 1}/{len(questions)} questions")
        
        # Calculate overall accuracy
        accuracy = correct_retrievals / len(questions) if questions else 0
        
        # Compile evaluation results
        evaluation = {
            "accuracy": accuracy,
            "k": k,
            "num_questions": len(questions),
            "correct_retrievals": correct_retrievals,
            "results": results
        }
        
        return evaluation

    def process_dataset(self, dataset_id: str, k: int = 2):
        """
        Process a dataset by loading it, creating a vector database, and evaluating retrieval.
        
        Args:
            dataset_id: ID of the dataset to process
            k: Number of documents to retrieve for evaluation
        """
        # Load the dataset
        print(f"Loading dataset: {dataset_id}")
        chunked_documents, questions = self.load_dataset(dataset_id)
        
        # Create the vector database with unique collection name based on k
        print(f"Creating/accessing vector database for: {dataset_id} with k={k}")
        collection = self.create_collection(dataset_id, chunked_documents, k=k)
        
        # Evaluate retrieval performance
        print(f"Evaluating retrieval performance (k={k})")
        evaluation = self.evaluate_retrieval(collection, questions, k=k)
        
        # Save the evaluation results
        output_file = os.path.join(self.data_dir, f"{dataset_id}_evaluation_k{k}.json")
        with open(output_file, 'w') as f:
            json.dump(evaluation, f, indent=2)
            
        print(f"Saved evaluation results to: {output_file}")
        print(f"Retrieval accuracy: {evaluation['accuracy']:.2f} ({evaluation['correct_retrievals']}/{evaluation['num_questions']})")

    def list_available_datasets(self) -> List[str]:
        """
        List all available datasets in the data directory.
        
        Returns:
            List of dataset IDs
        """
        datasets = []
        
        # Check the chunks directory for dataset files
        if os.path.exists(self.chunks_dir):
            for file in os.listdir(self.chunks_dir):
                if file.endswith(".json"):
                    dataset_id = file.replace(".json", "")
                    
                    # Check if the corresponding questions file exists
                    questions_file = os.path.join(self.questions_dir, f"{dataset_id}_questions.json")
                    if os.path.exists(questions_file):
                        datasets.append(dataset_id)
        
        return datasets

def main():
    parser = argparse.ArgumentParser(description='Create ChromaDB vector database and evaluate retrieval')
    parser.add_argument('--data_dir', type=str, default='data',
                        help='Directory containing the processed data')
    parser.add_argument('--db_dir', type=str, default='vectordb',
                        help='Directory to store the ChromaDB database')
    parser.add_argument('--dataset_id', type=str,
                        help='ID of the dataset to process (if not specified, will list available datasets)')
    parser.add_argument('--k', type=int, default=2,
                        help='Number of documents to retrieve for evaluation')
    
    args = parser.parse_args()
    
    # Create the vector database creator
    creator = VectorDatabaseCreator(
        data_dir=args.data_dir,
        db_dir=args.db_dir
    )
    print(creator.list_available_datasets())
    # If dataset ID is not specified, list available datasets
    if args.dataset_id is None:
        datasets = creator.list_available_datasets()
        if datasets:
            print("Available datasets:")
            for dataset in datasets:
                print(f"  - {dataset}")
            print("To process a dataset, specify --dataset_id")
        else:
            print("No datasets found. Run process_data.py first to create datasets.")
        return
    
    # Process the specified dataset
    creator.process_dataset(args.dataset_id, k=args.k)

if __name__ == "__main__":
    main()
