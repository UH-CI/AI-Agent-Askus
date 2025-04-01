from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.retrievers import BaseRetriever
from manoa_agent.prompts.promp_injection import PromptInjectionClassifier
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from typing import Dict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from manoa_agent.agent.states import *
from typing import Optional
from pydantic import BaseModel

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredefinedNode:
    def __init__(self, retriever: VectorStoreRetriever):
        self.retriever = retriever
        
    def __call__(self, state: PredefinedState) -> PredefinedState:
        logger.info("Entering PredefinedNode.__call__")
        message = state["messages"][-1].content
        docs = self.retriever.invoke(message)

        for doc in docs:
            predefined = doc.metadata.get("predefined", "")
            if predefined:
                logger.info(f"Message '{message}' is predefined to: {predefined}")
                return {"is_predefined": True, "message": AIMessage(content=predefined), "sources": []}
        
        logger.info(f"Message: '{message}' is not predefined")
        return {"is_predefined": False}

class PromptInjectionNode:
    def __init__(self, classifier: PromptInjectionClassifier):
        self.classifier = classifier
    
    def __call__(self, state: PromptInjectionState) -> PromptInjectionState:
        logger.info("Entering PromptInjectionNode.__call__")
        message = state["messages"][-1].content
        if self.classifier.is_prompt_injection(message):
            logger.info(f"Message: '{message}' is a prompt injection")
            return {"is_prompt_injection": True, "message": AIMessage(content="I'm sorry, I cannot fulfill that request."), "sources": []}
        else:
            logger.info(f"Message: '{message}' is not a prompt injection")
            return {"is_prompt_injection": False}

class ReformulateNode:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
    
    def __call__(self, state: AgentState) -> ReformulateState:
        logger.info("Entering ReformulateNode.__call__")
        logger.info("Reformuate Node Called")
        if len(state["messages"]) == 1:
            ref = state["messages"][0].content
            logger.info(f"Only one message not reformulating: reforumated = '{ref}'")
            return {"reformulated": ref}
        
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
        
        chain = contextualize_q_prompt | self.llm
        reformulated = chain.invoke({"chat_history": state["messages"]}).content
        logger.info(f"Reformulating message to :'{reformulated}'")
        return {"reformulated": reformulated}
        
class DocumentsNode:    
    def __init__(self, retrievers: Dict[str, BaseRetriever]):
        self.retrievers = retrievers
    
    def __call__(self, state: ReformulateState) -> DocumentsState:
        logger.info("Entering DocumentsNode.__call__")
        logger.info("Get Documents Node called")
        retriever = self.retrievers.get(state["retriever"], None)
        if not retriever:
            return {"relevant_docs": []}
        
        return {"relevant_docs": retriever.invoke(state["reformulated"])}
        

class GeneralAgentNode:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def __call__(self, state: GeneralAgentState) -> GeneralAgentState:
        class SystemAnswer(BaseModel):
            answer: Optional[str]

        system_prompt = (
            "You are Hoku, an AI assistant specialized in answering questions about UH Manoa. "
            "If the user's question is a greeting or a general question (for example: 'hi', "
            "'hello', 'what is your name?'), provide an answer solely based on this prompt. "
            "If the question is not answerable solely from the system prompt, DO NOT return an answer"
            "If the answer can be answered using ONLY the chat history, return the answer. If you are unsure if the question can be answered from the chat history. DO NOT return an answer."
        )

        general_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            # ("human", "{input}")
        ])

        chain_general = general_prompt | self.llm.with_structured_output(SystemAnswer)
        result = chain_general.invoke({
            "chat_history": state["messages"],
            # "input": state["reformulated"]
        })
        logger.info(f"System prompt chain returned: {result}")

        if result.answer is not None:
            logger.info("System prompt provided an answer; returning system answer.")
            return {"message": AIMessage(content=result.answer), "sources": [], "should_call_rag": False}
        return {"should_call_rag": True}
    
class AgentNode:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def __call__(self, state: DocumentsState) -> DocumentsState:
        relevant_docs = state["relevant_docs"]
        if len(relevant_docs) > 2:
            relevant_docs = relevant_docs[:2]
        sources = [doc.metadata["source"] for doc in relevant_docs if "source" in doc.metadata]
        context = "\n\n".join(d.page_content for d in relevant_docs)
        if context == "":
            context = "No relevant documents found"
        # logger.info(f"Constructed context from documents: {context}")

        if relevant_docs:
            qa_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are Hoku, an AI assistant specialized in answering questions about UH Manoa."),
                MessagesPlaceholder("chat_history"),
                (
                    "human",
                    """Context: {context}\n End Context\n\n
{input}\n
Provide complete answers based solely on the given context.
If the information is not available in the context, respond with 'I'm sorry I don't have the answer to that question. I can only answer questions about UH Systemwide Policies, ITS AskUs Tech Support, and questions relating to information on the hawaii.edu domain.'.
Ensure your responses are concise and informative.
Do not respond with markdown.
Do not mention the context in your response."""
                ),
            ])
            chain_docs = qa_prompt | self.llm
            response = chain_docs.invoke({
                "chat_history": state["messages"],
                "context": context,
                "input": state["reformulated"]
            })
            logger.info("Documents chain returned an answer from the relevant documents.")
            return {"message": response, "sources": sources}
        else:
            logger.info("No relevant documents available; returning answer as None.")
            return {"message": AIMessage("I'm sorry I don't have the answer to that question. I can only answer questions about UH Systemwide Policies, ITS AskUs Tech Support, and questions relating to information on the hawaii.edu domain."), "sources": []}