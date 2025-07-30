#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to evaluate RAG system responses against gold standard answers.

This script:
1. Reads questions and gold standard answers from a JSON file
2. Queries the API endpoint with each question
3. Evaluates responses using multiple metrics:
   - BERTScore
   - ROUGE-L/ROUGE-Lsum
   - BLEURT
   - Embedding cosine similarity (using Gemini)
   - LLM-based evaluation (using Gemini)
4. Outputs evaluation results to a JSON file
"""

import os
import json
import argparse
import requests
import time
import numpy as np
from typing import Dict, List, Any, Tuple, Union
from tqdm import tqdm
import google.generativeai as genai
from sklearn.metrics.pairwise import cosine_similarity

# For BERTScore and ROUGE
import torch
from bert_score import BERTScorer
from rouge_score import rouge_scorer

# Try to import BLEURT if available
try:
    import tensorflow as tf
    from bleurt import score as bleurt_score
    BLEURT_AVAILABLE = True
except ImportError:
    BLEURT_AVAILABLE = False
    print("BLEURT not available. BLEURT evaluation will be skipped.")


class RAGEvaluator:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize the RAG evaluator.
        
        Args:
            api_key: Google API key for Gemini
            model_name: Name of the Gemini model to use
        """
        self.api_endpoint = "http://localhost:3000/api/trpc/chat.response?batch=1"
        self.api_key = api_key
        self.model_name = model_name
        
        # Initialize evaluation metrics
        self.bert_scorer = BERTScorer(lang="en", rescale_with_baseline=True)
        self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL', 'rougeLsum'], use_stemmer=True)
        
        # Initialize BLEURT if available
        if BLEURT_AVAILABLE:
            checkpoint = "bleurt-base-128"  # You might need to download this or use a different one
            self.bleurt_scorer = bleurt_score.BleurtScorer(checkpoint)
        
        # Initialize Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        self.embedding_model = genai.GenerativeModel("embedding-001")
    
    def load_evaluation_data(self, json_path: str) -> List[Dict[str, Any]]:
        """
        Load questions and gold standard answers from JSON file.
        
        Args:
            json_path: Path to the evaluation questions JSON file
            
        Returns:
            List of question dictionaries with gold standard answers
        """
        with open(json_path, 'r') as f:
            questions = json.load(f)
        
        print(f"Loaded {len(questions)} questions with gold standard answers from {json_path}")
        return questions
    
    def query_endpoint(self, question: str, retriever: str = "general") -> str:
        """
        Query the endpoint with the given question.
        
        Args:
            question: The question to ask
            retriever: The retriever type to use (general, policy, etc.)
            
        Returns:
            The AI's response to the question
        """
        payload = {
            "0": {
                "json": {
                    "input": [
                        {
                            "type": "ai",
                            "content": "Aloha! my name is Hoku! I can assist you with UH Systemwide Policies, ITS AskUs Tech Support, and questions relating to information on the hawaii.edu domain."
                        },
                        {
                            "type": "human",
                            "content": question
                        }
                    ],
                    "retriever": retriever
                }
            }
        }
        
        try:
            response = requests.post(self.api_endpoint, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            ai_message = response_data[0]["result"]["data"]["json"]["message"]
            
            if ai_message["type"] == "ai":
                return ai_message["content"]
            else:
                return ""
        except Exception as e:
            print(f"Error querying endpoint: {e}")
            return ""
    
    def compute_bertscore(self, candidate: str, reference: str) -> Dict[str, float]:
        """
        Compute BERTScore metrics.
        
        Args:
            candidate: The candidate response
            reference: The reference (gold standard) response
            
        Returns:
            Dictionary with BERTScore metrics (precision, recall, F1)
        """
        with torch.no_grad():
            P, R, F1 = self.bert_scorer.score([candidate], [reference])
            return {
                "bertscore_precision": P.item(),
                "bertscore_recall": R.item(),
                "bertscore_f1": F1.item()
            }
    
    def compute_rouge(self, candidate: str, reference: str) -> Dict[str, Dict[str, float]]:
        """
        Compute ROUGE metrics.
        
        Args:
            candidate: The candidate response
            reference: The reference (gold standard) response
            
        Returns:
            Dictionary with ROUGE metrics
        """
        scores = self.rouge_scorer.score(reference, candidate)
        return {
            "rouge1": {
                "precision": scores["rouge1"].precision,
                "recall": scores["rouge1"].recall,
                "fmeasure": scores["rouge1"].fmeasure
            },
            "rouge2": {
                "precision": scores["rouge2"].precision,
                "recall": scores["rouge2"].recall,
                "fmeasure": scores["rouge2"].fmeasure
            },
            "rougeL": {
                "precision": scores["rougeL"].precision,
                "recall": scores["rougeL"].recall,
                "fmeasure": scores["rougeL"].fmeasure
            },
            "rougeLsum": {
                "precision": scores["rougeLsum"].precision,
                "recall": scores["rougeLsum"].recall,
                "fmeasure": scores["rougeLsum"].fmeasure
            }
        }
    
    def compute_bleurt(self, candidate: str, reference: str) -> Dict[str, float]:
        """
        Compute BLEURT score.
        
        Args:
            candidate: The candidate response
            reference: The reference (gold standard) response
            
        Returns:
            Dictionary with BLEURT score
        """
        if not BLEURT_AVAILABLE:
            return {"bleurt": None}
        
        scores = self.bleurt_scorer.score([reference], [candidate])
        return {"bleurt": scores[0]}
    
    def compute_embedding_similarity(self, candidate: str, reference: str) -> Dict[str, float]:
        """
        Compute embedding cosine similarity using Gemini embeddings.
        
        Args:
            candidate: The candidate response
            reference: The reference (gold standard) response
            
        Returns:
            Dictionary with embedding similarity score
        """
        try:
            # Get embeddings
            candidate_embedding = self.embedding_model.generate_embeddings(candidate)
            reference_embedding = self.embedding_model.generate_embeddings(reference)
            
            # Convert to numpy arrays
            candidate_vector = np.array(candidate_embedding.embedding)
            reference_vector = np.array(reference_embedding.embedding)
            
            # Reshape for sklearn's cosine_similarity
            candidate_vector = candidate_vector.reshape(1, -1)
            reference_vector = reference_vector.reshape(1, -1)
            
            # Compute cosine similarity
            similarity = cosine_similarity(candidate_vector, reference_vector)[0][0]
            
            return {"embedding_similarity": similarity}
        except Exception as e:
            print(f"Error computing embedding similarity: {e}")
            return {"embedding_similarity": None}
    
    def llm_evaluation(self, candidate: str, reference: str, question: str) -> Dict[str, Any]:
        """
        Use Gemini to evaluate the quality of the candidate answer compared to the reference.
        
        Args:
            candidate: The candidate response
            reference: The reference (gold standard) response
            question: The original question
            
        Returns:
            Dictionary with LLM evaluation results
        """
        prompt = f"""
        You are an expert evaluator of question-answering systems. Please evaluate the quality of a candidate answer compared to a reference (gold standard) answer.
        
        Question: {question}
        
        Reference Answer: {reference}
        
        Candidate Answer: {candidate}
        
        Please rate the candidate answer on the following criteria using a scale from 1 to 5 (where 5 is the best):
        - Relevance: How directly does the answer address the question?
        - Accuracy: How factually correct is the answer compared to the reference?
        - Completeness: How complete is the answer compared to the reference?
        - Conciseness: Is the answer appropriately concise or too verbose?
        
        Also provide an overall score from 1 to 5 and a brief explanation of your rating.
        
        Format your response as a JSON object with the following keys:
        {{
            "relevance": <score>,
            "accuracy": <score>,
            "completeness": <score>,
            "conciseness": <score>,
            "overall": <score>,
            "explanation": "<your explanation>"
        }}
        
        Provide only the JSON object, nothing else.
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from the response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].strip()
            
            # Parse JSON
            evaluation = json.loads(response_text)
            
            return {
                "llm_evaluation": evaluation
            }
        except Exception as e:
            print(f"Error in LLM evaluation: {e}")
            return {
                "llm_evaluation": {
                    "error": str(e)
                }
            }
    
    def evaluate_question(self, question_data: Dict[str, Any], retriever: str = "general") -> Dict[str, Any]:
        """
        Evaluate a single question-answer pair.
        
        Args:
            question_data: Dictionary with question data (including gold standard answer)
            retriever: Retriever type to use
            
        Returns:
            Dictionary with evaluation results
        """
        question = question_data["question"]
        reference = question_data["answer"]
        
        # Query the endpoint
        print(f"Querying endpoint for question: {question[:50]}...")
        candidate = self.query_endpoint(question, retriever)
        
        if not candidate:
            print("Failed to get a response from the endpoint.")
            return {
                "question": question,
                "reference": reference,
                "candidate": None,
                "metrics": None
            }
        
        # Compute all evaluation metrics
        print("Computing evaluation metrics...")
        bertscore_metrics = self.compute_bertscore(candidate, reference)
        rouge_metrics = self.compute_rouge(candidate, reference)
        bleurt_metrics = self.compute_bleurt(candidate, reference)
        embedding_metrics = self.compute_embedding_similarity(candidate, reference)
        # llm_metrics = self.llm_evaluation(candidate, reference, question)
        
        # Combine all metrics
        metrics = {
            **bertscore_metrics,
            "rouge": rouge_metrics,
            **bleurt_metrics,
            **embedding_metrics,
            # **llm_metrics
        }
        
        return {
            "question": question,
            "reference": reference,
            "candidate": candidate,
            "metrics": metrics
        }
    
    def evaluate_all(self, questions: List[Dict[str, Any]], retriever: str = "general") -> List[Dict[str, Any]]:
        """
        Evaluate all questions.
        
        Args:
            questions: List of question dictionaries
            retriever: Retriever type to use
            
        Returns:
            List of evaluation results
        """
        results = []
        
        for i, question_data in enumerate(tqdm(questions, desc="Evaluating questions")):
            print(f"\nEvaluating question {i+1}/{len(questions)}")
            result = self.evaluate_question(question_data, retriever)
            results.append(result)
            
            # Add a small delay to avoid overloading the endpoint
            if i < len(questions) - 1:
                time.sleep(2)
        
        return results
    
    def compute_aggregate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute aggregate metrics across all evaluated questions.
        
        Args:
            results: List of evaluation results
            
        Returns:
            Dictionary with aggregate metrics
        """
        # Filter out results with None metrics
        valid_results = [r for r in results if r["metrics"] is not None]
        
        if not valid_results:
            return {"error": "No valid evaluation results to aggregate"}
        
        # Initialize aggregate metrics
        aggregate = {
            "bertscore_precision": [],
            "bertscore_recall": [],
            "bertscore_f1": [],
            "rouge1_f1": [],
            "rouge2_f1": [],
            "rougeL_f1": [],
            "rougeLsum_f1": [],
            "bleurt": [],
            "embedding_similarity": [],
            "llm_overall": []
        }
        
        # Collect individual metrics
        for result in valid_results:
            metrics = result["metrics"]
            
            # BERTScore
            if "bertscore_precision" in metrics:
                aggregate["bertscore_precision"].append(metrics["bertscore_precision"])
                aggregate["bertscore_recall"].append(metrics["bertscore_recall"])
                aggregate["bertscore_f1"].append(metrics["bertscore_f1"])
            
            # ROUGE
            if "rouge" in metrics:
                rouge = metrics["rouge"]
                aggregate["rouge1_f1"].append(rouge["rouge1"]["fmeasure"])
                aggregate["rouge2_f1"].append(rouge["rouge2"]["fmeasure"])
                aggregate["rougeL_f1"].append(rouge["rougeL"]["fmeasure"])
                aggregate["rougeLsum_f1"].append(rouge["rougeLsum"]["fmeasure"])
            
            # BLEURT
            if "bleurt" in metrics and metrics["bleurt"] is not None:
                aggregate["bleurt"].append(metrics["bleurt"])
            
            # Embedding similarity
            if "embedding_similarity" in metrics and metrics["embedding_similarity"] is not None:
                aggregate["embedding_similarity"].append(metrics["embedding_similarity"])
            
            # LLM evaluation
            if "llm_evaluation" in metrics and "overall" in metrics["llm_evaluation"]:
                aggregate["llm_overall"].append(metrics["llm_evaluation"]["overall"])
        
        # Calculate means
        mean_metrics = {}
        for key, values in aggregate.items():
            if values:
                mean_metrics[f"mean_{key}"] = sum(values) / len(values)
        
        return mean_metrics

    def save_results(self, results: List[Dict[str, Any]], aggregate: Dict[str, Any], output_path: str):
        """
        Save evaluation results to a JSON file.
        
        Args:
            results: List of evaluation results
            aggregate: Aggregate metrics
            output_path: Path to save the results
        """
        output = {
            "individual_results": results,
            "aggregate_metrics": aggregate,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "num_questions": len(results)
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"Saved evaluation results to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Evaluate RAG system responses against gold standard answers')
    
    parser.add_argument('--input', type=str, default='testing/data/data/evaluation_questions.json',
                        help='Path to the evaluation questions JSON file')
    
    parser.add_argument('--output', type=str, default='testing/data/evaluation_results.json',
                        help='Path to save the evaluation results')
    
    parser.add_argument('--api_key', type=str, required=True,
                        help='Google API key for accessing Gemini')
    
    parser.add_argument('--retriever', type=str, default='general',
                        help='Retriever type to use (general, policy, etc.)')
    
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit the number of questions to evaluate')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Initialize the evaluator
    evaluator = RAGEvaluator(api_key=args.api_key)
    
    # Load questions and gold standard answers
    questions = evaluator.load_evaluation_data(args.input)
    
    # Limit the number of questions if specified
    if args.limit and args.limit > 0:
        questions = questions[:args.limit]
        print(f"Limiting evaluation to {args.limit} questions")
    
    # Evaluate all questions
    results = evaluator.evaluate_all(questions, args.retriever)
    
    # Compute aggregate metrics
    aggregate = evaluator.compute_aggregate_metrics(results)
    
    # Print summary of aggregate metrics
    print("\nAggregate Metrics:")
    for key, value in aggregate.items():
        print(f"{key}: {value:.4f}")
    
    # Save results
    evaluator.save_results(results, aggregate, args.output)
    
    print(f"\nEvaluation complete. Processed {len(results)} questions.")
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
