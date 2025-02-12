from dotenv import load_dotenv
from embeddings import convert
from openai import OpenAI
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from chromadb import HttpClient
from prompts.promp_injection import load
from retrievers.graphdb import GraphVectorRetriever
from neo4j_graphrag.retrievers import VectorRetriever
import neo4j


from typing import Sequence
from langchain_core.messages import BaseMessage, AIMessage
from typing import TypedDict
from langchain_chroma import Chroma
from langgraph.graph import END, StateGraph, START, MessagesState
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document

import os

load_dotenv(override=True)

neo4j_driver = neo4j.GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))
)

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

faq_retriever = its_faq_collection.as_retriever(
    search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

policies_retriever = policies_collection.as_retriever(
    search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

vector_retriever = VectorRetriever(
   neo4j_driver,
   index_name="text_embeddings",
   embedder=embedder,
   return_properties=["text"]
)

graph_retriever = GraphVectorRetriever(retriever=vector_retriever)

# llm = ChatOllama(model=os.getenv("OLLAMA_MODEL"), base_url=os.getenv("OLLAMA_HOST"))
llm = ChatOpenAI(model="gpt-4o")


prompt_injection_classifier = load(embedder=embedder, load_path="data/prompt_injection_model/injection_model.joblib")

class AgentState(MessagesState):
    retriever: str

class ChatHistoryCheckState(AgentState):
    can_answer_from_history: bool

class ReformulatedOutputState(AgentState):
    reformulated: str

class GetDocumentsOutputState(AgentState):
    relevant_docs: Sequence[Document]

class AgentInputState(AgentState, ChatHistoryCheckState, ReformulatedOutputState, GetDocumentsOutputState):
    pass

class AgentOutputState(TypedDict):
    message: BaseMessage
    sources: Sequence[str]

def call_model(state: AgentInputState) -> AgentOutputState:
    system_prompt = """You are Hoku, an AI assistant specialized in answering questions about UH Manoa."""

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", """Context: {context}\n End Context\n\n
         {input}\n
         Provide complete answers based solely on the given context.
         If the information is not available in the context, respond with 'I don't know'.
         Ensure your responses are concise and informative.
         Do not respond with markdown.
         Do not mention the context in your response."""),
    ])

    relevant_docs = state['relevant_docs']
    context = "\n\n".join(d.page_content for d in relevant_docs)

    if context == "":
        context = "No relevant documents found."

    chain = qa_prompt | llm
    response = chain.invoke({
        "chat_history": state["messages"],
        "context": context,
        "input": state['reformulated']
    })

    relevant_docs_with_sources = [doc.metadata["source"] for doc in relevant_docs if "source" in doc.metadata]

    return {"message": response, "sources": relevant_docs_with_sources}

def answer_from_history(state: ChatHistoryCheckState) -> AgentOutputState:
    system_prompt = """You are Hoku, an assistant for answering questions about UH Manoa.
    Answer the latest question using ONLY information from the chat history.
    If you cannot fully answer the question from the chat history, respond with "I don't know"."""

    history_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
    ])
    
    chain = history_prompt | llm
    response = chain.invoke({"chat_history": state["messages"]})
    return {"message": response, "sources": []}

def check_chat_history(state: AgentState) -> ChatHistoryCheckState:
    if len(state["messages"]) <= 1:
        return {"can_answer_from_history": False}
    
    system_prompt = """Given the chat history and the latest question, determine if the question can be fully answered using ONLY the information present in the chat history.
    Return 'yes' if it can be answered completely from chat history, 'no' if it requires additional information.
    Only analyze - do not answer the question."""

    check_history_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
    ])
    
    chain = check_history_prompt | llm
    result = chain.invoke({"chat_history": state["messages"]}).content.lower()
    return {"can_answer_from_history": "yes" in result}

def greeting_agent(state: AgentState):
    system_prompt = (
        "You are Hoku, an assistant for answering questions about UH Manoa.\n"
        "Provide accurate and concise answers based solely on the given context.\n"
        "If the information is not available in the context, respond with 'I'm sorry, I don't know the answer to that'.\n"
        "Answer politely and concisely.\n"
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("query"),
        ]
    )

    chain = qa_prompt | llm
    response = chain.invoke({"query": state["messages"]})
    return {"message": response, "sources": []}

def reformulate_query(state: AgentState) -> ReformulatedOutputState:
    if len(state["messages"]) == 1:
        return {"reformulated": state["messages"][0].content}
    
    contextualize_q_system_prompt = (
        "Given the chat history and the latest user question, "
        "rephrase the question to be self-contained and clear without relying on the chat history. "
        "Ensure the reformulated question retains the original intent and context. "
        "Do NOT answer the question. "
        "Only return the reformulated question if needed, otherwise return it as is."
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
        ]
    )
    
    chain = contextualize_q_prompt | llm
    reformulated = chain.invoke({"chat_history": state["messages"]}).content
    return {"reformulated": reformulated}

def get_documents(state: ReformulatedOutputState) -> GetDocumentsOutputState:
    reformulated = state["reformulated"]

    if state["retriever"] == "askus":
        relevant_docs = faq_retriever.invoke(reformulated)
    elif state["retriever"] == "policies":
        relevant_docs = policies_retriever.invoke(reformulated)
    elif state["retriever"] == "graphdb":
        relevant_docs = graph_retriever.invoke(reformulated) 
    else:
        relevant_docs = []

    if len(relevant_docs) > 2:
        relevant_docs = relevant_docs[:2]
    
    return {"relevant_docs": relevant_docs}

def should_call_agent(state: GetDocumentsOutputState):
    return len(state["relevant_docs"]) > 0

def is_prompt_injection(state: AgentState):
    last_message = state["messages"][-1]
    is_injection = prompt_injection_classifier.is_prompt_injection(last_message.content)
    return "prompt_injection" if is_injection else "safe"

def handle_error(state) -> AgentOutputState:
    message = AIMessage(content="I'm sorry, I cannot fulfill that request.")
    return {"message": message, "sources": []}

def should_use_rag(state: ChatHistoryCheckState):
    return "rag" if not state["can_answer_from_history"] else "history"

# Compile Agent with new workflow
workflow = StateGraph(input=AgentState, output=AgentOutputState)

# Add nodes
workflow.add_node("handle_error", handle_error)
workflow.add_node("check_chat_history", check_chat_history)
workflow.add_node("answer_from_history", answer_from_history)
workflow.add_node("reformulate_query", reformulate_query)
workflow.add_node("get_documents", get_documents)
workflow.add_node("rag_agent", call_model)

# Add edges with new logic
workflow.add_conditional_edges(
    START,
    is_prompt_injection,
    {
        "prompt_injection": "handle_error",
        "safe": "check_chat_history",
    }
)

workflow.add_conditional_edges(
    "check_chat_history",
    should_use_rag,
    {
        "history": "answer_from_history",
        "rag": "reformulate_query",
    }
)

workflow.add_edge("reformulate_query", "get_documents")
workflow.add_edge("get_documents", "rag_agent")
workflow.add_edge("rag_agent", END)
workflow.add_edge("answer_from_history", END)
workflow.add_edge("handle_error", END)

agent = workflow.compile()

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