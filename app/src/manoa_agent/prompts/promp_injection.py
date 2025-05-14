import csv
import os

import joblib  # Used for saving and loading the model
import numpy as np
from datasets import load_dataset
from sklearn.linear_model import LogisticRegression

from manoa_agent.embeddings.base import Embedder


class PromptInjectionClassifier:
    def __init__(self, model: LogisticRegression, embedder: Embedder):
        self.model = model
        self.embedder = embedder

    def is_prompt_injection(self, query: str) -> bool:
        query_embedding = self.embedder.embed_query(query)
        query_embedding = np.array(query_embedding)
        # Wrap query_embedding in a list so that predict expects a 2D array.
        prediction = self.model.predict([query_embedding])[0]
        return bool(prediction)


def train(
    embedder: Embedder, csv_path: str, save_path: str = ""
) -> PromptInjectionClassifier:
    """
    Train a PromptInjectionClassifier using the deepset/prompt-injections dataset combined with
    additional data from a CSV file. The CSV file should have a header with columns "label" and "text".
    If a save_path is provided (non-empty string), the trained model is saved.

    Args:
        embedder (Embedder): An instance of an Embedder.
        csv_path (str): File path to the CSV file containing additional classification data.
        save_path (str, optional): Path to save the trained model. Defaults to "".

    Returns:
        PromptInjectionClassifier: The trained classifier.
    """
    # Load the existing dataset from deepset/prompt-injections.
    prompt_injection_ds = load_dataset("deepset/prompt-injections")
    train_set = prompt_injection_ds["train"]
    train_X, train_y = list(train_set["text"]), list(train_set["label"])

    # Load additional data from CSV file.
    if csv_path and os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                text = row["text"]
                try:
                    # Convert label to int (assuming it's 0 or 1)
                    label = int(row["label"])
                except ValueError:
                    continue  # Skip row if label conversion fails
                train_X.append(text)
                train_y.append(label)
    else:
        print(f"CSV file at {csv_path} not found, skipping additional data.")

    # Embed the documents.
    embedded_train_X = embedder.embed_documents(train_X)
    embedded_train_X = np.array(embedded_train_X)

    # Train the Logistic Regression model.
    model = LogisticRegression(random_state=0).fit(embedded_train_X, train_y)

    # Save the model if a save_path is provided.
    if save_path:
        joblib.dump(model, save_path)

    return PromptInjectionClassifier(model=model, embedder=embedder)


def load(embedder: Embedder, load_path: str) -> PromptInjectionClassifier:
    """
    Load a saved LogisticRegression model from the given load_path and return a
    PromptInjectionClassifier using the provided embedder. If the provided load_path
    does not exist, raise a FileNotFoundError.

    Args:
        embedder (Embedder): An instance of an Embedder.
        load_path (str): The file path from where to load the model.

    Returns:
        PromptInjectionClassifier: The classifier with the loaded model.
    """
    if not os.path.exists(load_path):
        raise FileNotFoundError(
            f"Model file not found at {load_path}. Please train the model first."
        )
    model = joblib.load(load_path)
    return PromptInjectionClassifier(model=model, embedder=embedder)
