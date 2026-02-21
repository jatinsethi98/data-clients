"""Embedding backends with abstract base."""

from data_clients.embeddings.base import BaseEmbedder
from data_clients.embeddings.voyage import VoyageEmbedder
from data_clients.embeddings.openai import OpenAIEmbedder
from data_clients.embeddings.ollama import OllamaEmbedder

__all__ = [
    "BaseEmbedder",
    "VoyageEmbedder",
    "OpenAIEmbedder",
    "OllamaEmbedder",
]
