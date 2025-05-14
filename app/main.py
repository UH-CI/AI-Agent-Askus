from dotenv import load_dotenv
from manoa_agent.embeddings import convert
from openai import OpenAI
from langchain_chroma import Chroma

from chromadb import HttpClient
from langchain_openai import ChatOpenAI
# from langchain_google_genai import GoogleGenerativeAI
from manoa_agent.prompts.promp_injection import load
# from manoa_agent.retrievers.graphdb import GraphVectorRetriever
# from neo4j_graphrag.retrievers import VectorRetriever
import neo4j
from langchain_chroma import Chroma
from langgraph.graph import END, StateGraph, START

import os

load_dotenv(override=True)

# neo4j_driver = neo4j.GraphDatabase.driver(
#     os.getenv('NEO4J_URI'),
#     auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))
# )

embedder = convert.from_open_ai(OpenAI(), "text-embedding-3-large")
http_client = HttpClient(os.getenv("CHROMA_HOST"), os.getenv("CHROMA_PORT"))

its_faq_collection = Chroma(
    collection_name="its_faq",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"}
)

policies_collection = Chroma(
    collection_name="uh_policies",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"}
)

general_collection = Chroma(
    collection_name="general_faq",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"}
)

predefined_collection = Chroma(
    collection_name="predefined",
    client=http_client,
    embedding_function=embedder,
    collection_metadata={"hnsw:space": "cosine"}
)

faq_retriever = its_faq_collection.as_retriever(
    search_type="similarity", search_kwargs={"k": 2}
    # search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

# policies_retriever = policies_collection.as_retriever(
#     search_type="similarity", search_kwargs={"k": 2}
#     search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
# )

policies_retriever = policies_collection.as_retriever(
    search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

general_retriever = general_collection.as_retriever(
    search_type="similarity", search_kwargs={"k": 2}
    # search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

predefined_retriever = predefined_collection.as_retriever(
    search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.95}
)

# vector_retriever = VectorRetriever(
#    neo4j_driver,
#    index_name="text_embeddings",
#    embedder=embedder,
#    return_properties=["text"]
# )

# graph_retriever = GraphVectorRetriever(retriever=vector_retriever)

retrievers = {
    "askus": faq_retriever,
    "policies": policies_retriever,
    "general": general_retriever
}

llm = ChatOpenAI(model="gpt-4o")
# llm = ChatOllama(model=os.getenv("OLLAMA_MODEL"), base_url=os.getenv("OLLAMA_HOST"))
# llm = ChatOpenAI(model="gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"), base_url=os.getenv("GEMINI_BASE_URL"))
# llm = GoogleGenerativeAI(model="gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))


prompt_injection_classifier = load(embedder=embedder, load_path="data/prompt_injection_model/injection_model.joblib")

from manoa_agent.agent.states import *
from manoa_agent.agent.nodes import *

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def predefined_condition(state: PredefinedState):
    logger.info("Evaluating predefined_condition")
    if state["is_predefined"]:
        logger.info("predefined_condition: state is predefined")
        return "predefined"
    else:
        logger.info("predefined_condition: state is not predefined, branching to prompt_injection")
        return "prompt_injection"

def prompt_injection_condition(state: PromptInjectionState):
    logger.info("Evaluating prompt_injection_condition")
    if state["is_prompt_injection"]:
        logger.info("prompt_injection_condition: state is prompt injection")
        return "prompt_injection"
    else:
        logger.info("prompt_injection_condition: state is safe")
        return "safe"

def rag_agent_condition(state: GeneralAgentState):
    if state["should_call_rag"]:
        return "rag_agent"
    else:
        return "answered"


workflow = StateGraph(AgentState, output=AgentOutputState)

workflow.add_node("predefined", PredefinedNode(retriever=predefined_retriever))
workflow.add_node("prompt_injection", PromptInjectionNode(prompt_injection_classifier))
workflow.add_node("reformulate", ReformulateNode(llm = llm))
workflow.add_node("get_documents", DocumentsNode(retrievers=retrievers))
workflow.add_node("rag_agent", AgentNode(llm = llm))
workflow.add_node("general_agent", GeneralAgentNode(llm = llm))

workflow.add_edge(START, "predefined")
workflow.add_edge("reformulate", "get_documents")
workflow.add_edge("get_documents", "rag_agent")
workflow.add_edge("rag_agent", END)

workflow.add_conditional_edges("prompt_injection", prompt_injection_condition, {"prompt_injection": END, "safe": "general_agent"})
workflow.add_conditional_edges("predefined", predefined_condition, {"predefined": END, "prompt_injection": "prompt_injection"})
workflow.add_conditional_edges("general_agent", rag_agent_condition, {"rag_agent": "reformulate", "answered": END})

agent = workflow.compile()
logger.info("Workflow compiled successfully")

from fastapi import FastAPI
from langserve import add_routes
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Agent AskUs",
    version="1.1",
    description="A simple api server using Langchain's Runnable interfaces",
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_routes(
    app,
    agent,
    path="/askus",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)