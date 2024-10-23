import yaml
import operator
from typing import Annotated, Sequence
from langchain_core.messages import BaseMessage, AIMessage
from typing import Annotated, TypedDict
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.graph import END, StateGraph, START, MessagesState
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datasets import load_dataset
from sklearn.linear_model import LogisticRegression
from langchain_core.documents import Document
import numpy as np
from langchain.retrievers import EnsembleRetriever
from fastapi.middleware.cors import CORSMiddleware


# Load Config
with open("config.yml", "r") as f:
    config = yaml.safe_load(f)


# Load Embedding Model
model_name = config["embedding"]
model_kwargs = {'device': 'cuda', "trust_remote_code": True}

embedding_model = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
)


# Load Vector Store
vector_store = Chroma(
    collection_name="its_faq",
    persist_directory="db",
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

vector_store_policies = Chroma(
    collection_name="uh_policies",
    persist_directory="db",
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

# Create Retriever
retriever = vector_store.as_retriever(
    search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

policy_retriever = vector_store_policies.as_retriever(
    search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

print(retriever.invoke("what is laulima?"))
# lotr = EnsembleRetriever(retrievers=[retriever, policy_retriever], search_kwargs={"k": 2})
# lotr = EnsembleRetriever(retrievers=[retriever], search_kwargs={"k": 2})


# Train Prompt Injection Classifier
prompt_injection_ds = load_dataset("deepset/prompt-injections")

train = prompt_injection_ds["train"]
train_X, train_y = train["text"], train["label"]
train_X = embedding_model.embed_documents(train_X)
train_X = np.array(train_X)

test = prompt_injection_ds["test"]
test_X, test_y = test["text"], test["label"]
test_X = embedding_model.embed_documents(test_X)
test_X = np.array(test_X)

prompt_injection_classifier = LogisticRegression(random_state=0).fit(train_X, train_y)


# Init LLM
llm = ChatOllama(model=config['llm'], temperature=0)


# Create State

class AgentState(MessagesState):
    retriever: str

class ReformulatedOutputState(AgentState):
    reformulated: str

class GetDocumentsOutputState(AgentState):
    relevant_docs: Sequence[Document]

class AgentInputState(AgentState, ReformulatedOutputState, GetDocumentsOutputState):
    pass

class AgentOutputState(TypedDict):
    message: BaseMessage
    sources: Sequence[str]

# Create Agent
def call_model(state: AgentInputState) -> AgentOutputState:
    system_prompt = (
        "You are an assistant for answering questions about UH Manoa."
        "Fully answer the question given ONLY the provided context.\n"
        "If the answer DOES NOT appear in the context, say 'I'm sorry I don't know the answer to that'.\n"
        "Keep your answer concise and informative.\n"
        "DO NOT mention the context, users do not see it.\n\n"
        "context\n{context}"
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "Answer in a few sentences. If you cant find the answer say 'I dont know'.\nquestion: {input}"),
        ]
    )

    new_query = state['reformulated']
    messages = state['messages']
    relevant_docs = state['relevant_docs']

    context = "\n\n".join(d.page_content for d in relevant_docs)

    chain = qa_prompt | llm
    response = chain.invoke(
        {
            "chat_history": messages,
            "context": context,
            "input": new_query
        }
    )

    return {"message": response, "sources": [doc.metadata["source"] for doc in relevant_docs]}

def greeting_agent(state: AgentState):
    system_prompt = (
        "Your name is Hoku. You are an assistant for answering questions about UH Manoa.\n"
        "You were initially created during the Hawaii Annual Code Challenge by team DarkMode.\n"
        "You are currently under development.\n"
        "Respond ONLY with information given here. If you do not see the answer here say I'm sorry I do not know the answer to that.\n"
        "Answer concisely and polite.\n"
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
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question. "
        "just reformulate it if needed and otherwise return it as is. "
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
        relevant_docs = retriever.invoke(reformulated)
    elif state["retriever"] == "policies":
        relevant_docs = policy_retriever.invoke(reformulated)
    else:
        relevant_docs = []

    if len(relevant_docs) > 2:
        relevant_docs = relevant_docs[:2]
    
    return {"relevant_docs": relevant_docs}

def should_call_agent(state: GetDocumentsOutputState):
    return len(state["relevant_docs"]) > 0

def is_prompt_injection(state: AgentState):
    last_message = state["messages"][-1]
    embedding = embedding_model.embed_query(last_message.content)
    is_injection = prompt_injection_classifier.predict([embedding])[0]
    return "prompt_injection" if is_injection else "safe"

def handle_error(state: AgentState) -> AgentOutputState:
    message = "I'm sorry, I cannot fulfill that request."
    return {"message": AIMessage(content=message), "sources": []}


# Compile Agent
workflow = StateGraph(input=AgentState, output=AgentOutputState)

workflow.add_node("handle_error", handle_error)
workflow.add_node("reformulate_query", reformulate_query)
workflow.add_node("get_documents", get_documents)
workflow.add_node("rag_agent", call_model)
workflow.add_node("greeting_agent", greeting_agent)

workflow.add_conditional_edges(START, is_prompt_injection, {"prompt_injection": "handle_error", "safe": "reformulate_query"})
workflow.add_conditional_edges("get_documents", should_call_agent, {True: "rag_agent", False: "greeting_agent"})

workflow.add_edge("reformulate_query", "get_documents")
workflow.add_edge("greeting_agent", END)
workflow.add_edge("rag_agent", END)
workflow.add_edge("handle_error", END)

agent = workflow.compile()

from fastapi import FastAPI
from langserve import add_routes

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