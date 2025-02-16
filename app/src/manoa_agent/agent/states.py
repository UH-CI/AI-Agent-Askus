from typing import Sequence, TypedDict, List
from langchain.schema import BaseMessage, Document
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    retriever: str

class AgentOutputState(TypedDict):
    message: BaseMessage
    sources: List[str]

class PredefinedState(AgentState, AgentOutputState):
    is_predefined: bool

class PromptInjectionState(AgentState, AgentOutputState):
    is_prompt_injection: bool

class ReformulateState(AgentState, AgentOutputState):
    reformulated: str

class DocumentsState(AgentState, AgentOutputState, ReformulateState):
    relevant_docs: Sequence[Document]

class GeneralAgentState(ReformulateState):
    should_call_rag: bool
