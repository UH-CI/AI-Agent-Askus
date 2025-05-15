"""This example illustrates how to get started easily with the SimpleKGPipeline
and ingest text into a Neo4j Knowledge Graph.

This example assumes a Neo4j db is up and running. Update the credentials below
if needed.

NB: when building a KG from text, no 'Document' node is created in the Knowledge Graph.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv(override=True)

import neo4j
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.experimental.pipeline.pipeline import PipelineResult
from neo4j_graphrag.experimental.pipeline.types.schema import (
    EntityInputType,
    RelationInputType,
)
from neo4j_graphrag.experimental.components.text_splitters.base import TextSplitter
from neo4j_graphrag.experimental.components.types import TextChunks, TextChunk


from neo4j_graphrag.experimental.components.text_splitters.base import TextSplitter
from neo4j_graphrag.experimental.components.types import TextChunks, TextChunk


class LineSplitter(TextSplitter):
    def __init__(self, chunk_size: int):
        self.chunk_size = chunk_size

    async def run(self, text: str) -> TextChunks:
        # Split on newlines, preserving line breaks
        lines = text.splitlines(keepends=True)
        result_chunks: list[str] = []
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) <= self.chunk_size:
                current_chunk += line
            else:
                if current_chunk:
                    result_chunks.append(current_chunk)
                if len(line) > self.chunk_size:
                    # overly long line becomes its own chunk
                    result_chunks.append(line)
                    current_chunk = ""
                else:
                    current_chunk = line

        if current_chunk:
            result_chunks.append(current_chunk)

        # Now wrap with indexes so TextChunk.validate passes:
        text_chunks = [
            TextChunk(text=chunk, index=i) for i, chunk in enumerate(result_chunks)
        ]
        return TextChunks(chunks=text_chunks)


from neo4j_graphrag.llm import LLMInterface, VertexAILLM
from neo4j_graphrag.llm import OpenAILLM
from vertexai.generative_models import GenerationConfig

logging.basicConfig()
logging.getLogger("neo4j_graphrag").setLevel(logging.DEBUG)
# logging.getLogger("neo4j_graphrag").setLevel(logging.INFO)


# Neo4j db infos
URI = os.getenv("NEO4J_URI")
AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))
DATABASE = "neo4j"

# Text to process
TEXT = ""
with open("../data/course-data/abbreviation.txt", "r") as f:
    TEXT += f.read()
with open("../data/course-data/degrees.txt", "r") as f:
    TEXT += f.read()
with open("../data/course-data/catalog.json", "r") as f:
    TEXT += f.read()

# Define the entity types
ENTITIES: list[EntityInputType] = [
    {
        "label": "Course",
        "description": "A university course, identified by subject code and number, with title, credits, and description",
    },
    {
        "label": "Department",
        "description": "An academic department or program offering the course (e.g. ‘Architecture’, ‘Tropical Medicine and Medical Microbiology’)",
    },
    {
        "label": "College",
        "description": "An academic college or school that departments belong to (e.g. ‘College of Arts, Languages & Letters’)",
    },
]

# Define the relations between those entities
RELATIONS: list[RelationInputType] = [
    {
        "label": "OFFERED_BY",
        "description": "Links a Course to the Department that offers it",
    },
    {
        "label": "PART_OF",
        "description": "Links a Department to the College or School it belongs to",
    },
    {
        "label": "HAS_PREREQUISITE",
        "description": "Links a Course to another Course that must be completed first",
        "properties": [{"name": "gradeRequirement", "type": "STRING"}],
    },
    {
        "label": "CROSS_LISTED_WITH",
        "description": "Links a Course to another Course code with which it is cross-listed",
    },
]

# Suggest the schema the pipeline should enforce
POTENTIAL_SCHEMA = [
    ("Course", "OFFERED_BY", "Department"),
    ("Department", "PART_OF", "College"),
    ("Course", "HAS_PREREQUISITE", "Course"),
    ("Course", "CROSS_LISTED_WITH", "Course"),
]


async def define_and_run_pipeline(
    neo4j_driver: neo4j.Driver,
    llm: LLMInterface,
) -> PipelineResult:
    # Create an instance of the SimpleKGPipeline
    kg_builder = SimpleKGPipeline(
        llm=llm,
        driver=neo4j_driver,
        embedder=OpenAIEmbeddings(),
        text_splitter=LineSplitter(chunk_size=3000),
        entities=ENTITIES,
        relations=RELATIONS,
        potential_schema=POTENTIAL_SCHEMA,
        from_pdf=False,
        neo4j_database=DATABASE,
    )
    return await kg_builder.run_async(text=TEXT)


async def main() -> PipelineResult:
    generation_config = GenerationConfig(temperature=0.0)
    llm = VertexAILLM(
        model_name="models/gemini-2.5-pro-preview-05-06",
        generation_config=generation_config,
    )
    with neo4j.GraphDatabase.driver(URI, auth=AUTH) as driver:
        res = await define_and_run_pipeline(driver, llm)
    # await llm.async_client.close()
    return res


if __name__ == "__main__":
    res = asyncio.run(main())
    print(res)
