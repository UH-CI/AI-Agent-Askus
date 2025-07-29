import logging
import json
import os
import datetime
from typing import Dict, List, Set
from collections import defaultdict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from manoa_agent.agent.states import DocumentsState, ReformulateState

# Set up console logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up file logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Create a file handler for detailed logs
file_logger = logging.getLogger('detailed_logs')
file_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(os.path.join(log_dir, 'rerank_logs.jsonl'), mode='a')
file_handler.setFormatter(logging.Formatter('%(message)s'))
file_logger.addHandler(file_handler)
file_logger.propagate = False  # Don't send to root logger

cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')


def log_to_file(data):
    """Log structured data to a file in JSON format"""
    try:
        # Add timestamp
        data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Convert Document objects to dictionaries
        if 'unranked_chunks' in data:
            data['unranked_chunks'] = [
                {
                    'content': doc.page_content,
                    'metadata': doc.metadata
                } for doc in data['unranked_chunks']
            ]
        
        if 'reranked_chunks' in data:
            data['reranked_chunks'] = [
                {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': doc.metadata.get('rerank_score', 0.0)
                } for doc in data['reranked_chunks']
            ]
            
        # Log as JSON
        file_logger.info(json.dumps(data))
    except Exception as e:
        logger.error(f"Error logging data to file: {e}")

class EnhancedDocumentsNode:
    """Enhanced DocumentsNode that retrieves chunks directly for reranking."""
    
    def __init__(self, retrievers: Dict[str, BaseRetriever]):
        self.retrievers = retrievers

    def __call__(self, state: ReformulateState) -> DocumentsState:
        logger.info("Enhanced Get Documents Node called")
        retriever = self.retrievers.get(state["retriever"], None)
        if not retriever:
            return {"relevant_docs": []}

        # Get chunk-level documents from retriever
        chunk_docs = retriever.invoke(state["reformulated"])
        logger.info(f"Retrieved {len(chunk_docs)} chunks for reranking")
        
        # Store the doc_id with each chunk for tracking sources
        for chunk in chunk_docs:
            if "doc_id" not in chunk.metadata and "full_document" in chunk.metadata:
                # If doc_id is missing but we have a full document, generate a simple hash
                chunk.metadata["doc_id"] = str(hash(chunk.metadata["full_document"][:100]))[:8]
        
        return {"relevant_docs": chunk_docs}


class EnhancedAgentNode:
    """Enhanced AgentNode with cross-encoder reranking."""
    
    def __init__(self, llm: BaseChatModel, cross_encoder_model: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.llm = llm
        logger.info(f"Initialized cross-encoder model: {cross_encoder_model}")

    def _rerank_chunks(self, query: str, chunks: List[Document], top_k: int = 3) -> List[Document]:
        """Rerank chunks using cross-encoder and return top_k chunks."""
        if not chunks:
            return []
            
        # Prepare input pairs (query, chunk_content)
        # Show the entire chunk to the cross-encoder model
        pairs = [(query, chunk.page_content) for chunk in chunks]
        
        # Get relevance scores from cross-encoder
        scores = cross_encoder.predict(pairs)
        
        # Rank by score (higher is better)
        scored_chunks = list(zip(chunks, scores))
        reranked = sorted(scored_chunks, key=lambda x: x[1], reverse=True)
        
        # Log reranking results
        logger.info("Cross-encoder chunk-level reranking results:")
        for i, (chunk, score) in enumerate(reranked[:top_k]):
            source = chunk.metadata.get("source", "Unknown")
            doc_id = chunk.metadata.get("doc_id", "Unknown")
            content_preview = chunk.page_content[:100].replace('\n', ' ')
            logger.info(f"  {i+1}. Score: {score:.3f} - DocID: {doc_id} - Content: {content_preview}...")
        
        # Add rerank scores to metadata and return top chunks
        top_chunks = []
        for chunk, score in reranked[:top_k]:
            # Create a copy with rerank score added to metadata
            new_metadata = chunk.metadata.copy()
            new_metadata["rerank_score"] = float(score)
            
            reranked_chunk = Document(
                page_content=chunk.page_content,
                metadata=new_metadata
            )
            top_chunks.append(reranked_chunk)
            
        return top_chunks

    def __call__(self, state: DocumentsState) -> DocumentsState:
        relevant_docs = state["relevant_docs"]
        if not relevant_docs:
            logger.info("No relevant documents available; returning default message.")
            return {
                "message": AIMessage(
                    "I'm sorry I don't have the answer to that question. I can only answer questions about UH Systemwide Policies, ITS AskUs Tech Support, and questions relating to information on the hawaii.edu domain."
                ),
                "sources": [],
            }
        
        query = state["message"]
        logger.info(f"Processing query: {query}")
        logger.info(f"Found {len(relevant_docs)} chunks to rerank")
        
        # Log unranked chunks
        logger.info("Logging unranked chunks for inspection")
        
        # Rerank chunks using cross-encoder and get top 5
        reranked_chunks = self._rerank_chunks(query, relevant_docs, top_k=10)
        
        # Extract sources from reranked chunks
        sources = []
        for chunk in reranked_chunks:
            source = chunk.metadata.get("source", "Unknown")
            # Also try url field as backup for source
            if source == "Unknown" and "url" in chunk.metadata:
                source = chunk.metadata["url"]
            sources.append(source)
            
        # Remove duplicates but preserve order
        unique_sources = []
        for source in sources:
            if source not in unique_sources:
                unique_sources.append(source)
        
        # Join reranked chunks for context
        context = "\n\n".join(chunk.page_content for chunk in reranked_chunks)
        
        logger.info(f"Using top {len(reranked_chunks)} reranked chunks for context from {len(unique_sources)} sources")
        
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are Hoku, an AI assistant specialized in answering questions about UH Manoa.",
                ),
                MessagesPlaceholder("chat_history"),
                (
                    "human",
                    """Context: {context}\n End Context\n\n
{input}\n
Provide complete answers based solely on the given context.
If the information is not available in the context, respond with 'I'm sorry I don't have the answer to that question. I can only answer questions about UH Systemwide Policies, ITS AskUs Tech Support, and questions relating to information on the hawaii.edu domain.'.
Ensure your responses are concise and informative.
Do not respond with markdown.
Do not mention the context in your response.""",
                ),
            ]
        )
        
        chain_docs = qa_prompt | self.llm
        response = chain_docs.invoke(
            {
                "chat_history": state["messages"],
                "context": context,
                "input": state["message"],
            }
        )
        
        # Log everything to file
        log_data = {
            'query': query,
            'unranked_chunks': relevant_docs,
            'reranked_chunks': reranked_chunks,
            'sources': unique_sources,
            'answer': response.content,
            'prompt_context': context
        }
        # log_to_file(log_data)
        
        logger.info("Enhanced documents chain returned an answer using the top reranked chunks.")
        return {"message": response, "sources": unique_sources[:2]}
