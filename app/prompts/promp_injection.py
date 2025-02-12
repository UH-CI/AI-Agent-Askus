from embeddings.base import Embedder
from sklearn.linear_model import LogisticRegression
from datasets import load_dataset
import numpy as np
import joblib  # Used for saving and loading the model
import os

class PromptInjectionClassifier:
    def __init__(self, model: LogisticRegression, embedder: Embedder):
        self.model = model
        self.embedder = embedder

    def is_prompt_injection(self, query: str) -> bool:
        query_embedding = self.embedder.embed_query(query)
        query_embedding = np.array(query_embedding)
        # Note: We wrap query_embedding in a list so that predict expects a 2D array.
        prediction = self.model.predict([query_embedding])[0]
        return bool(prediction)


def train(embedder: Embedder, save_path: str = "") -> PromptInjectionClassifier:
    """
    Train a PromptInjectionClassifier using the deepset/prompt-injections dataset.
    If a save_path is provided (non-empty string), the trained model is saved.

    Args:
        embedder (Embedder): An instance of an Embedder.
        save_path (str, optional): Path to save the trained model. Defaults to "".

    Returns:
        PromptInjectionClassifier: The trained classifier.
    """
    prompt_injection_ds = load_dataset("deepset/prompt-injections")

    # Process training data.
    train_set = prompt_injection_ds["train"]
    train_X, train_y = train_set["text"], train_set["label"]
    train_X = embedder.embed_documents(train_X)
    train_X = np.array(train_X)

    # Process test data (optional: can be used for evaluation).
    test_set = prompt_injection_ds["test"]
    test_X, test_y = test_set["text"], test_set["label"]
    test_X = embedder.embed_documents(test_X)
    test_X = np.array(test_X)

    model = LogisticRegression(random_state=0).fit(train_X, train_y)

    # Save the model if a path is provided.
    if save_path != "":
        joblib.dump(model, save_path)

    return PromptInjectionClassifier(model=model, embedder=embedder)


def load(embedder: Embedder, load_path: str) -> PromptInjectionClassifier:
    """
    Load a saved LogisticRegression model from the given load_path and return
    a PromptInjectionClassifier using the provided embedder. If the provided
    load_path does not exist, train a new model (and save it) before returning.

    Args:
        embedder (Embedder): An instance of an Embedder.
        load_path (str): The file path from where to load the model.

    Returns:
        PromptInjectionClassifier: The classifier with the loaded or newly trained model.
    """
    if not os.path.exists(load_path):
        # If the model file doesn't exist, train a new model and save it.
        classifier = train(embedder, save_path=load_path)
    else:
        model = joblib.load(load_path)
        classifier = PromptInjectionClassifier(model=model, embedder=embedder)
    return classifier