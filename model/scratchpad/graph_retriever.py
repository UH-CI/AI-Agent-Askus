import os
import neo4j
from dotenv import load_dotenv
import logging

from neo4j_graphrag.llm import OpenAILLM, OllamaLLM
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.generation.graphrag import GraphRAG
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.indexes import create_vector_index

logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv(override=True)
# Initialize the Neo4j driver
neo4j_driver = neo4j.GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))
)

# Set up the OpenAI LLM, embedder, and KG builder components:
llm = OpenAILLM(
    api_key = os.getenv('OPENAI_API_KEY2'),
    model_name="gpt-4o",
    model_params={
        "max_tokens": 2000,
    },
)

llm2 = OllamaLLM(
    model_name="llama3.3:70b-instruct-q3_K_M",
    host='http://128.171.215.18'
)


embedder = OpenAIEmbeddings(model="text-embedding-3-large")

create_vector_index(neo4j_driver, name="text_embeddings", label="Chunk", 
                    embedding_property="embedding", dimensions=3072, similarity_fn="cosine")

# 2. KG Retriever
vector_retriever = VectorRetriever(
   neo4j_driver,
   index_name="text_embeddings",
   embedder=embedder,
   return_properties=["text"]
)

# print(vector_retriever.get_search_results(query_text="tell me more about the academic calendar policy at uh manoa", top_k=1))

rag = GraphRAG(llm=llm2, retriever=vector_retriever)

response = rag.search("who do i contact for questions relating to these policies?", return_context=True)

print(response.answer)