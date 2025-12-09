"""
Agentic Enhanced Agent Node with Fallback Search
Implements multi-step retrieval with alternative query generation
"""

import logging
from typing import List, Dict, Any, Set
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from sentence_transformers import CrossEncoder

from manoa_agent.agent.states import DocumentsState

logger = logging.getLogger(__name__)

# Initialize cross-encoder globally to avoid reloading
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

class AlternativeQueries(BaseModel):
    """Model for alternative query generation"""
    queries: List[str] = Field(description="List of 3 alternative search phrases")
    reasoning: str = Field(description="Brief explanation of the alternative approaches")

class AgenticEnhancedNode:
    """Enhanced AgentNode with agentic fallback search capability."""
    
    def __init__(self, llm: BaseChatModel, retriever, cross_encoder_model: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.llm = llm
        self.retriever = retriever
        logger.info(f"Initialized agentic enhanced node with cross-encoder: {cross_encoder_model}")

    def _rerank_chunks(self, query: str, chunks: List[Document], top_k: int = 5) -> List[Document]:
        """Rerank chunks using cross-encoder and return top_k chunks."""
        if not chunks:
            return []
            
        # Prepare input pairs (query, chunk_content)
        pairs = [(query, chunk.page_content) for chunk in chunks]
        
        # Get relevance scores from cross-encoder
        scores = cross_encoder.predict(pairs)
        
        # Rank by score (higher is better)
        scored_chunks = list(zip(chunks, scores))
        reranked = sorted(scored_chunks, key=lambda x: x[1], reverse=True)
        
        # Log reranking results
        logger.info(f"Cross-encoder reranking results for query: '{query[:50]}...'")
        for i, (chunk, score) in enumerate(reranked[:top_k]):
            source = chunk.metadata.get("source", "Unknown")
            doc_id = chunk.metadata.get("doc_id", "Unknown")
            content_preview = chunk.page_content[:100].replace('\n', ' ')
            logger.info(f"  {i+1}. Score: {score:.3f} - DocID: {doc_id} - Content: {content_preview}...")
        
        # Add rerank scores to metadata and return top chunks
        top_chunks = []
        for chunk, score in reranked[:top_k]:
            new_metadata = chunk.metadata.copy()
            new_metadata["rerank_score"] = float(score)
            
            reranked_chunk = Document(
                page_content=chunk.page_content,
                metadata=new_metadata
            )
            top_chunks.append(reranked_chunk)
            
        return top_chunks

    def _extract_unique_sources(self, chunks: List[Document]) -> List[str]:
        """Extract unique sources from chunks, preserving order."""
        sources = []
        seen_sources = set()
        
        for chunk in chunks:
            source = chunk.metadata.get("source", "Unknown")
            # Also try url field as backup
            if source == "Unknown" and "url" in chunk.metadata:
                source = chunk.metadata["url"]
            
            if source not in seen_sources:
                sources.append(source)
                seen_sources.add(source)
                
        return sources

    def _generate_alternative_queries(self, original_query: str) -> List[str]:
        """Generate alternative search queries using LLM."""
        
        parser = PydanticOutputParser(pydantic_object=AlternativeQueries)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at generating alternative search queries to help find relevant information.
Given an original question, generate 3 different search phrases that could help find the same information using different keywords, synonyms, or approaches.

Focus on:
1. Using different technical terms or synonyms
2. Breaking down complex questions into simpler parts  
3. Using more specific or more general terms
4. Considering different ways users might phrase the same need

For IT/technical questions, consider alternative software names, processes, or user scenarios.

{format_instructions}"""),
            ("human", "Original question: {query}\n\nGenerate 3 alternative search phrases:")
        ])
        
        formatted_prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        chain = formatted_prompt | self.llm | parser
        
        try:
            result = chain.invoke({"query": original_query})
            logger.info(f"Generated alternative queries for '{original_query[:50]}...': {result.queries}")
            return result.queries
        except Exception as e:
            logger.error(f"Failed to generate alternative queries: {e}")
            # Fallback to simple variations
            return [
                f"how to {original_query.lower()}",
                f"steps for {original_query.lower()}",
                f"guide {original_query.lower()}"
            ]

    def _generate_refined_queries(self, original_query: str, previous_queries: List[str]) -> List[str]:
        """Generate refined search queries based on previous attempts."""
        
        parser = PydanticOutputParser(pydantic_object=AlternativeQueries)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at generating refined search queries when previous attempts have failed.
You will be given an original question and the alternative search phrases that were already tried but didn't find relevant content.

Your task is to generate 3 NEW search phrases that take a completely different approach:

1. **Broader context**: Try more general terms or related concepts
2. **Different terminology**: Use completely different technical terms, abbreviations, or synonyms
3. **User perspective**: Think about how different types of users might describe the same problem
4. **Process focus**: Focus on the underlying process rather than specific steps
5. **Problem-solution angle**: Frame as problems users might face rather than instructions

Avoid repeating similar concepts from the previous attempts. Be creative and think outside the box.

{format_instructions}"""),
            ("human", """Original question: {original_query}

Previous search attempts that failed:
{previous_queries}

Generate 3 completely different search approaches:""")
        ])
        
        formatted_prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        chain = formatted_prompt | self.llm | parser
        
        previous_queries_text = "\n".join([f"- {q}" for q in previous_queries])
        
        try:
            result = chain.invoke({
                "original_query": original_query,
                "previous_queries": previous_queries_text
            })
            logger.info(f"Generated refined queries for '{original_query[:50]}...': {result.queries}")
            return result.queries
        except Exception as e:
            logger.error(f"Failed to generate refined queries: {e}")
            # Fallback to more creative variations
            return [
                f"troubleshoot {original_query.lower()}",
                f"fix issues with {original_query.lower()}",
                f"configure {original_query.lower()}"
            ]

    def _perform_fallback_search(self, original_query: str, alternative_queries: List[str]) -> List[Document]:
        """Perform fallback search using alternative queries and deduplicate by source."""
        
        all_chunks = []
        seen_doc_ids = set()
        
        logger.info(f"Performing fallback search with {len(alternative_queries)} alternative queries")
        
        for i, alt_query in enumerate(alternative_queries, 1):
            logger.info(f"Fallback search {i}/3: '{alt_query}'")
            
            try:
                # Retrieve chunks for this alternative query
                chunks = self.retriever.invoke(alt_query)
                logger.info(f"  Retrieved {len(chunks)} chunks")
                
                # Add unique chunks (deduplicate by doc_id)
                new_chunks = 0
                for chunk in chunks:
                    doc_id = chunk.metadata.get("doc_id", f"unknown_{len(all_chunks)}")
                    if doc_id not in seen_doc_ids:
                        all_chunks.append(chunk)
                        seen_doc_ids.add(doc_id)
                        new_chunks += 1
                
                logger.info(f"  Added {new_chunks} new unique chunks")
                
            except Exception as e:
                logger.error(f"Error in fallback search {i}: {e}")
                continue
        
        logger.info(f"Fallback search completed: {len(all_chunks)} total unique chunks from {len(seen_doc_ids)} unique sources")
        return all_chunks

    def _try_answer_with_context(self, query: str, context: str, sources: List[str], attempt_num: int) -> AIMessage:
        """Try to answer the question with given context."""
        
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are Hoku, an AI assistant specialized in answering questions about UH Manoa.
            
IMPORTANT: Only answer if the provided context contains relevant information to answer the question.
If the context does not contain sufficient relevant information, respond with:
'I'm sorry I don't have the answer to that question. I can only answer questions about UH Systemwide Policies, TeamDynamix Knowledgebase, ITS AskUs Tech Support, and questions relating to information on the hawaii.edu domain.'

When you do have relevant information:
- Provide complete answers based solely on the given context
- Be concise and informative
- Do not respond with markdown
- Do not mention the context in your response"""),
            MessagesPlaceholder("chat_history"),
            ("human", """Context: {context}\n End Context\n\n{input}"""),
        ])
        
        chain = qa_prompt | self.llm
        response = chain.invoke({
            "chat_history": [],  # We don't have chat history in this context
            "context": context,
            "input": query,
        })
        
        # Log the attempt
        is_sorry = "sorry" in response.content.lower() and "don't have" in response.content.lower()
        logger.info(f"Answer attempt {attempt_num}: {'❌ Sorry' if is_sorry else '✅ Real answer'} "
                   f"(Context: {len(context)} chars, Sources: {len(sources)})")
        
        return response

    def __call__(self, state: DocumentsState) -> DocumentsState:
        """Main processing method with agentic fallback search."""
        
        relevant_docs = state["relevant_docs"]
        query = state["message"]
        
        logger.info(f"🤖 AGENTIC ENHANCED NODE: Processing query: '{query}'")
        
        if not relevant_docs:
            logger.info("No relevant documents available; returning default message.")
            return {
                "message": AIMessage(
                    "I'm sorry I don't have the answer to that question. I can only answer questions about UH Systemwide Policies, TDX Knowledgebase, ITS AskUs Tech Support, and questions relating to information on the hawaii.edu domain."
                ),
                "sources": [],
            }
        
        logger.info(f"📊 Initial retrieval: {len(relevant_docs)} chunks")
        
        # STEP 1: Try with initial retrieval (k=10)
        logger.info("🔍 STEP 1: Trying with initial retrieval")
        
        # Rerank initial chunks
        reranked_chunks = self._rerank_chunks(query, relevant_docs, top_k=5)
        sources = self._extract_unique_sources(reranked_chunks)
        context = "\n\n".join(chunk.page_content for chunk in reranked_chunks)
        
        # Try to answer with initial context
        response = self._try_answer_with_context(query, context, sources, attempt_num=1)
        
        # Check if we got a "sorry" response
        is_sorry = "sorry" in response.content.lower() and "don't have" in response.content.lower()
        
        if not is_sorry:
            logger.info("✅ SUCCESS: Initial retrieval provided good answer")
            return {"message": response, "sources": sources[:2]}
        
        # STEP 2: Fallback search with alternative queries
        logger.info("🔄 STEP 2: Initial retrieval failed, trying fallback search")
        
        # Generate alternative queries
        alternative_queries = self._generate_alternative_queries(query)
        
        # Perform fallback search
        fallback_chunks = self._perform_fallback_search(query, alternative_queries)
        
        if not fallback_chunks:
            logger.info("❌ STEP 2 FAILED: No additional chunks found")
            # Continue to step 3 anyway
        
        # Combine original and fallback chunks, then rerank all
        all_chunks = relevant_docs + fallback_chunks
        logger.info(f"🔄 Combined chunks: {len(relevant_docs)} initial + {len(fallback_chunks)} fallback = {len(all_chunks)} total")
        
        # Rerank all chunks together
        step2_reranked = self._rerank_chunks(query, all_chunks, top_k=10)
        step2_sources = self._extract_unique_sources(step2_reranked)
        step2_context = "\n\n".join(chunk.page_content for chunk in step2_reranked)
        
        # Try to answer with expanded context
        step2_response = self._try_answer_with_context(query, step2_context, step2_sources, attempt_num=2)
        
        # Check step 2 result
        step2_is_sorry = "sorry" in step2_response.content.lower() and "don't have" in step2_response.content.lower()
        
        if not step2_is_sorry:
            logger.info("✅ SUCCESS: Step 2 fallback search provided good answer")
        else:
            logger.info("❌ FINAL FAILURE: Even fallback search couldn't find relevant content")
        
        return {"message": step2_response, "sources": step2_sources[:2]}
