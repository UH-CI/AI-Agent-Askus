from langchain_community.chat_models import ChatOllama
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import chain
from fastapi import FastAPI
from langchain.prompts import ChatPromptTemplate
from langserve import add_routes

model_name = 'dunzhang/stella_en_400M_v5'
model_kwargs = {'device': 'cuda', "trust_remote_code": True}

embedding_model = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
)

vector_store = Chroma(
    collection_name="faq",
    persist_directory="./model/db",
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

llm = ChatOllama(model="mistral-nemo:latest", temperature=0)

retriever = vector_store.as_retriever(
    search_kwargs={'k': 2}
)

contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question. "
    "just reformulate it if needed and otherwise return it as is. "
    "if there is no chat history, return the input as is. "
    "if the input is a greeting, return the input as is. "
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

history_aware_retriever = create_history_aware_retriever(
    llm, retriever, contextualize_q_prompt
)

system_prompt = (
    "Your name is Hoku. You are an assistant for answering questions about UH Manoa."
    "Answer the question given ONLY the provided context.\n"
    "If the answer DOES NOT appear in the context, say 'I'm sorry I don't know the answer to that'.\n"
    "Keep your answer concise and informative.\n"
    "DO NOT mention the context, users do not see it."
    "if the user greets you, greet them back nicely"
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "context:{context}\n\nquestion: {input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

sources_examples = [
    {"input": "Hi Hoku!", "output": "no"},
    {"input": "How are you?", "output": "no"},
    {"input": "What is duo mobile used for?", "output": "yes"},
    {"input": "what specs should i have for a mac laptop?", "output": "yes"},
    {"input": "Thank you!", "output": "no"},
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
        ("system", "Your job is to classify a user input as needing sources 'yes' or not needing sources 'no'."),
        few_shot_prompt,
        ("human", "{input}"),
    ]
)

def requires_source(inp: dict):
    chain = final_prompt | llm
    return "yes" in chain.invoke(inp).content.lower()


def add_sources_to_response_if_needed(inp: dict) -> dict:
    if not requires_source({"input" : inp["input"]}):
        return inp
    
    sources_text = "\n".join(list(set(doc.metadata["source"] for doc in inp['context'])))
    inp["answer"] = f"{inp['answer'].strip()}\n\nFor more information, check out these links\n{sources_text}"
    return inp

conversational_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer",
)

@chain
def langserve_input(text: str):
    return {"input" : text}

@chain
def langserve_output(inp: dict):
    return inp["answer"]

conversational_rag_chain_with_sources = langserve_input | conversational_rag_chain | add_sources_to_response_if_needed | langserve_output

app = FastAPI(
    title="AI Agent AskUs",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
)

add_routes(
    app,
    conversational_rag_chain_with_sources,
    path="/askus",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)