import yaml
import operator
from typing import Annotated, Sequence
from langchain_core.messages import BaseMessage
from typing import Annotated, TypedDict
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from datasets import load_dataset
from sklearn.linear_model import LogisticRegression
import numpy as np
from langchain.retrievers import EnsembleRetriever

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    reformulated: str

model_name = config["embedding"]
model_kwargs = {'device': 'cuda', "trust_remote_code": True}

embedding_model = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
)

vector_store = Chroma(
    collection_name="its_faq",
    persist_directory="db",
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

retriever = vector_store.as_retriever(
    search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

vector_store_policies = Chroma(
    collection_name="uh_policies",
    persist_directory="db",
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

policy_retriever = vector_store_policies.as_retriever(
    search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5}
)

policy_retriever.invoke("can you tell me about the academic calendar policy?")
lotr = EnsembleRetriever(retrievers=[retriever, policy_retriever], search_kwargs={"k": 2})

llm = ChatOpenAI(
    api_key="ollama",
    model=config["llm"],
    base_url="http://localhost:11434/v1",
    temperature=0,
)

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

# Added this helper function to handle message types.
# Converts messages to a list of respective message objects
def convert_to_message_objects(messages):
    chat_history = []
    for message in messages:
        if isinstance(message, (HumanMessage, AIMessage, SystemMessage)):
            chat_history.append(message)
        elif isinstance(message, dict) and 'type' in message and 'content' in message:
            if message['type'] == 'human':
                chat_history.append(HumanMessage(content=message['content']))
            elif message['type'] == 'ai':
                chat_history.append(AIMessage(content=message['content']))
            elif message['type'] == 'system':
                chat_history.append(SystemMessage(content=message['content']))
        else:
            chat_history.append(HumanMessage(content=str(message)))
    return chat_history

def call_model(state: AgentState):
    system_prompt = (
        "You are an assistant for answering questions about UH Manoa."
        "Fully answer the question given ONLY the provided context.\n"
        "If the answer DOES NOT appear in the context, say 'I'm sorry I don't know the answer to that'.\n"
        "Keep your answer concise and informative.\n"
        "DO NOT mention the context, users do not see it.\n"
        "context\n\n{context}"
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "Answer in a few sentences. If you can't find the answer say 'I don't know'.\nquestion: {input}"),
        ]
    )

    new_query = state['reformulated']
    messages = state['messages']
    relevant_docs = get_context(new_query)

    if len(relevant_docs) == 0:
        return {"messages": [AIMessage(content="I'm sorry, I could not find any relevant information to answer your question.")]}

    context = "\n\n".join(d.page_content for d in relevant_docs)

    chat_history = convert_to_message_objects(messages)

    chain = qa_prompt | llm
    response = chain.invoke(
        {
            "chat_history": chat_history,
            "context": context,
            "input": new_query
        }
    )
    sources_text = "\n".join(list(set(doc.metadata["source"] for doc in relevant_docs)))
    response.content = response.content + "\nFor more information, check out these links\n" + sources_text
    return {"messages": [response]}

def needs_source(state: AgentState):
    sources_examples = [
        {"input": "Hi Hoku!", "output": "no"},
        {"input": "Where is the ITS building located?", "output": "yes"},
        {"input": "Hello. What is your name?", "output": "no"},
        {"input": "What is duo mobile used for?", "output": "yes"},
        {"input": "How are you?", "output": "no"},
        {"input": "what specs should i have for a mac laptop?", "output": "yes"},
        {"input": "Thank you!", "output": "no"},
        {"input": "Who created you?", "output": "no"},
    ]

    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{input}"),
            ("ai", "{output}"),
        ]
    )

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=sources_examples,
        input_variables=["input"]
    )

    final_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Your job is to classify if a user query needs a source or not. response with yes or no."),
            few_shot_prompt,
            MessagesPlaceholder("input")
        ]
    )

    chain = final_prompt | llm
    last_message = HumanMessage(content=state["reformulated"])
    response = chain.invoke([last_message]).content.lower()
    return "needs_source" if "yes" in response else "greeting"

def greeting_agent(state: AgentState):
    system_prompt = (
        "Your name is Hoku. You are an assistant for answering questions about UH Manoa.\n"
        "You were initially created during the Hawaii Annual Code Challenge by team DarkMode.\n"
        "You are currently under development.\n"
        "Only respond with information given here.\n"
        "Answer nicely.\n"
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="query"),
            ("human", "{input}"),
        ]
    )

    chain = qa_prompt | llm

    # Adding to accomodate chat history
    last_message = state["messages"][-1]
    input_query = last_message.content if isinstance(last_message, HumanMessage) else str(last_message)
    
    response = chain.invoke({
        "query": state["messages"][:-1],
        "input": input_query
    })
    
    return {"messages": state["messages"] + [response]}



def reformulate_query(state: AgentState):
    if len(state["messages"]) == 1:
        return {"reformulated": state["messages"][0].content}
    
    contextualize_q_system_prompt = (
        "Given the chat history and the latest user question, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question. "
        "Just reformulate it if needed and otherwise return it as is."
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Latest question: {question}")
        ]
    )
    
    chain = contextualize_q_prompt | llm

    chat_history = convert_to_message_objects(state["messages"][:-1])

    latest_question = state["messages"][-1].content if isinstance(state["messages"][-1], HumanMessage) else str(state["messages"][-1])

    response = chain.invoke({
        "chat_history": chat_history,
        "question": latest_question
    })
    
    return {"reformulated": response.content}


def get_context(query: str):
    relevant_docs = lotr.invoke(query)
    if len(relevant_docs) > 2:
        return relevant_docs[:2]
    return relevant_docs

def is_prompt_injection(state: AgentState):
    last_message = state["messages"][-1]
    embedding = embedding_model.embed_query(last_message.content)
    is_injection = prompt_injection_classifier.predict([embedding])[0]
    return "prompt_injection" if is_injection else "safe"

def handle_error(state: AgentState):
    message = "Iʻm sorry, I cannot fulfill that request."
    return {"messages": [AIMessage(content=message)]}


workflow = StateGraph(AgentState)

workflow.add_node("greeting_agent", greeting_agent)
workflow.add_node("rag_agent", call_model)
workflow.add_node("handle_error", handle_error)
workflow.add_node("reformulate_query", reformulate_query)
workflow.add_conditional_edges("reformulate_query", needs_source, {"needs_source": "rag_agent", "greeting": "greeting_agent"})
workflow.add_edge("greeting_agent", END)
workflow.add_edge("rag_agent", END)
workflow.add_edge("handle_error", END)
workflow.add_conditional_edges(START, is_prompt_injection, {"prompt_injection": "handle_error", "safe": "reformulate_query"})

checkpointer = MemorySaver()

agent = workflow.compile(checkpointer=checkpointer)

from fastapi import FastAPI
from langserve import add_routes

app = FastAPI(
    title="AI Agent AskUs",
    version="1.1",
    description="A simple api server using Langchain's Runnable interfaces",
)

add_routes(
    app,
    agent,
    path="/askus",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)