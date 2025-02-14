from typing import Sequence, TypedDict
from langchain.schema import BaseMessage, Document
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    retriever: str

class ChatHistoryCheckState(AgentState):
    can_answer_from_history: bool

class ReformulatedOutputState(AgentState):
    reformulated: str

class GetDocumentsOutputState(AgentState):
    relevant_docs: Sequence[Document]

class AgentInputState(
    AgentState, ChatHistoryCheckState, ReformulatedOutputState, GetDocumentsOutputState
):
    pass

class AgentOutputState(TypedDict):
    message: BaseMessage
    sources: Sequence[str]
