from langchain.tools import tool
from typing import Optional, Type
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field, Extra
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain_core.output_parsers import StrOutputParser

class AnswerAboutSelfInput(BaseModel):
    query: str = Field(description="query about yourself")

class AnswerAboutSelf(BaseTool):
    name = "answer_about_self"
    description = "This tool is used to greet the user\nSay a farewell\nor to answer question related to yourself"
    args_schema: Type[BaseModel] = AnswerAboutSelfInput
    return_direct = True

    class Config:
        extra = Extra.allow

    def __init__(self, llm):
        super().__init__(llm=llm)
        self.llm = llm # not needed but helps with type hinting

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        system_prompt = (
            "Your name is Hoku. You are an assistant for answering questions about UH Manoa.\n"
            "You were initially created during the Hawaii Annual Code Challenge by team DarkMode.\n"
            "You are currently under development.\n"
        )

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{query}"),
            ]
        )

        chain = qa_prompt | self.llm | StrOutputParser
        return chain.invoke({"query": query})