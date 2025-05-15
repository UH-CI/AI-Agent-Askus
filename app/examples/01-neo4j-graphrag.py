from neo4j_graphrag.experimental.pipeline.types.schema import (
    EntityInputType,
    RelationInputType,
)
from neo4j_graphrag.llm import VertexAILLM
from vertexai.generative_models import GenerationConfig

generation_config = GenerationConfig(temperature=0.0)
llm = VertexAILLM(
    model_name="models/gemini-2.5-flash-preview-04-17",
    generation_config=generation_config,
)

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
