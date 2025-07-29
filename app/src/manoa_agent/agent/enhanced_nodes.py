import logging
from typing import Dict, List, Set
from collections import defaultdict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from manoa_agent.agent.states import DocumentsState, ReformulateState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedDocumentsNode:
    """Enhanced DocumentsNode that retrieves chunks but returns unique full documents."""
    
    def __init__(self, retrievers: Dict[str, BaseRetriever]):
        self.retrievers = retrievers

    def __call__(self, state: ReformulateState) -> DocumentsState:
        logger.info("Entering EnhancedDocumentsNode.__call__")
        logger.info("Enhanced Get Documents Node called")
        retriever = self.retrievers.get(state["retriever"], None)
        if not retriever:
            return {"relevant_docs": []}

        # Get chunk-level documents from retriever
        chunk_docs = retriever.invoke(state["reformulated"])
        
        # Extract unique full documents using doc_id
        unique_docs = {}
        for chunk_doc in chunk_docs:
            doc_id = chunk_doc.metadata.get("doc_id")
            full_content = chunk_doc.metadata.get("full_document")
            
            if doc_id and full_content and doc_id not in unique_docs:
                # Create a new document with full content
                full_doc = Document(
                    page_content=full_content,
                    metadata=chunk_doc.metadata.copy()
                )
                unique_docs[doc_id] = full_doc
        
        # Convert to list
        unique_doc_list = list(unique_docs.values())
        logger.info(f"Retrieved {len(chunk_docs)} chunks, reduced to {len(unique_doc_list)} unique documents")
        
        return {"relevant_docs": unique_doc_list}


class EnhancedAgentNode:
    """Enhanced AgentNode with cross-encoder reranking."""
    
    def __init__(self, llm: BaseChatModel, cross_encoder_model: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.llm = llm
        self.cross_encoder = CrossEncoder(cross_encoder_model)
        logger.info(f"Initialized cross-encoder model: {cross_encoder_model}")

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using period as delimiter."""
        # Split by period and filter out empty sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        # Add period back to each sentence for better context
        sentences = [s + '.' for s in sentences]
        return sentences

    def _rerank_sentences(self, query: str, sentences: List[str], sources: Dict[str, str], top_k: int = 5) -> List[Document]:
        """Rerank sentences using cross-encoder and return top_k as Documents."""
        if not sentences:
            return []
            
        # Prepare input pairs (query, sentence)
        pairs = [(query, sentence) for sentence in sentences]
        
        # Get relevance scores from cross-encoder
        scores = self.cross_encoder.predict(pairs)
        
        # Rank by score (higher is better)
        scored_sentences = list(zip(sentences, scores))
        reranked = sorted(scored_sentences, key=lambda x: x[1], reverse=True)
        
        # Log reranking results
        logger.info("Cross-encoder sentence-level reranking results:")
        for i, (sentence, score) in enumerate(reranked[:top_k]):
            logger.info(f"  {i+1}. Score: {score:.3f} - Sentence: {sentence[:50]}...")
        
        # Convert top sentences back to Documents
        top_sentences = reranked[:top_k]
        top_docs = []
        
        for sentence, score in top_sentences:
            # Try to find which source document this sentence came from
            source = "Unknown"
            for doc_content, doc_source in sources.items():
                if sentence in doc_content:
                    source = doc_source
                    break
                    
            # Create a Document for each top sentence
            doc = Document(
                page_content=sentence,
                metadata={
                    "source": source,
                    "rerank_score": score
                }
            )
            top_docs.append(doc)
            
        return top_docs

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
        
        query = state["reformulated"]
        logger.info(f"Processing query: {query}")
        logger.info(f"Found {len(relevant_docs)} unique full documents")
        
        # Extract all sentences from all documents
        all_sentences = []
        doc_sources = {}
        for doc in relevant_docs:
            # Store mapping of document content to source for later reference
            doc_sources[doc.page_content] = doc.metadata.get("source", "Unknown")
            
            # Split document into sentences
            sentences = self._split_into_sentences(doc.page_content)
            all_sentences.extend(sentences)
            
        logger.info(f"Extracted {len(all_sentences)} total sentences from all documents")
        
        # Rerank sentences and get top 5
        reranked_sentence_docs = self._rerank_sentences(query, all_sentences, doc_sources, top_k=5)
        
        # Use reranked sentences for context
        sources = [
            doc.metadata["source"] for doc in reranked_sentence_docs if "source" in doc.metadata
        ]
        # Remove duplicates but preserve order
        unique_sources = []
        for source in sources:
            if source not in unique_sources:
                unique_sources.append(source)
        
        # Join sentences for context
        context = "\n\n".join(d.page_content for d in reranked_sentence_docs)
        
        logger.info(f"Using top {len(reranked_sentence_docs)} reranked sentences for context from {len(unique_sources)} sources")
        
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
                "input": state["reformulated"],
            }
        )
        
        logger.info("Enhanced documents chain returned an answer using the top reranked sentences.")
        return {"message": response, "sources": unique_sources}
