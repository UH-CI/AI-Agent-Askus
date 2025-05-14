from pydantic import BaseModel
from typing import List
import json

# Define the Pydantic model
class Course(BaseModel):
    subject: str
    course_number: str
    title: str
    desc: str
    metadata: str

    def __str__(self):
        return f"{self.subject} {self.course_number}: {self.title}\nDescription: {self.desc}\nMetadata: {self.metadata}"

# Load the JSON file
file_path = 'data/catalog-1.json'  # Replace with the actual path to your JSON file
with open(file_path, 'r') as file:
    data = json.load(file)

# Parse the data using Pydantic
courses = [Course(**item) for item in data]

# Print the courses nicely
for course in courses[:3]:
    print(course)
    print()