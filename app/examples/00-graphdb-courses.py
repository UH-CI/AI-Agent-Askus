import asyncio
import os

from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_neo4j import Neo4jGraph


load_dotenv(override=True)

graph = Neo4jGraph(database="neo4j")

from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    temperature=0,
    model_name="models/gemini-2.5-flash-preview-04-17",
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL"),
)
llm2 = ChatOpenAI(temperature=0, model="gpt-4.1-mini")
llm3 = ChatOpenAI(
    temperature=0,
    model_name="gemini-2.0-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL"),
)
llm4 = ChatOpenAI(
    temperature=0,
    model_name="gemini-2.5-pro-preview-05-06",
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL"),
)

llm5 = ChatVertexAI(model_name="gemini-2.0-flash", temperature=0)

llm_transformer = LLMGraphTransformer(
    ignore_tool_usage=True,
    llm=llm5,
    allowed_nodes=[
        "Course",
        "Subject",
        "Program",
        "College",
        "Degree",  # e.g. Bachelor of Arts
        "Certificate",  # e.g. Minor, Post-bac Cert.
        "Abbreviation",  # e.g. “BA”, “PhD”, “MPH”, “CTAHR”
    ],
    allowed_relationships=[
        "BELONGS_TO",  # Course → Subject
        "PART_OF",  # Subject → College
        "OFFERS",  # Program → Degree/Certificate
        "HAS_ABBREV",  # Degree/Certificate/College/Subject → Abbreviation
        "REQUIRES",  # Course → Course (prereq)
        "CROSS_LISTED_AS",  # Course ↔ Course
        "REPEATABLE_UP_TO",  # Course → Course (max repeats)
    ],
    # node_properties=[
    #     # for Course, Subject, Program, College
    #     "title",
    #     "description",
    #     "credits",
    #     "course_number",
    #     "metadata",
    #     # for Degree/Certificate
    #     "full_name",
    #     # for Abbreviation
    #     "code",  # e.g. “BA”, “JD”, “CTAHR”
    # ],
    # relationship_properties=[
    #     "min_grade",  # PRE: requirements
    #     "max_repeats",  # how many times repeatable
    #     "cross_list_code",  # e.g. “ES 450” ↔ “WGSS 450”
    # ],
)


from langchain_core.documents import Document

with open("../data/course-data/catalog.json", "r") as f:
    catalog = f.read()

lines = catalog.splitlines()

chunks = ["\n".join(lines[i : i + 100]) for i in range(0, len(lines), 100)]

catalog_docs = [Document(page_content=chunk) for chunk in chunks]

with open("../data/course-data/abbreviation.txt", "r") as f:
    abbreviations = f.read()
with open("../data/course-data/degrees.txt", "r") as f:
    degrees = f.read()

documents = (
    [Document(page_content=abbreviations)]
    + catalog_docs
    + [Document(page_content=degrees)]
)


async def main():
    graph_documents = await llm_transformer.aconvert_to_graph_documents(documents)
    graph.add_graph_documents(graph_documents)
    # print(graph_documents)


if __name__ == "__main__":
    asyncio.run(main())
