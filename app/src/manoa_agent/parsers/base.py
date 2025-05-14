from abc import ABC, abstractmethod


class Parser(ABC):
    """
    Interface for Parsing Strings
    """

    @abstractmethod
    def parse(self, text: str) -> str:
        return text
