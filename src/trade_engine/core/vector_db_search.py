import sys

from openai import OpenAI
from pinecone import Pinecone

from trade_engine.config.openai_config import OPENAI_EMBEDDING_DIMENSION, OPENAI_EMBEDDING_MODEL, get_openai_api_key
from trade_engine.config.pinecone_config import get_pinecone_api_key, get_pinecone_index_name_eq
from trade_engine.exception.exception import CustomException
from trade_engine.logging.logger import logging


class VectorDBSearch:
    def __init__(self, index_name: str = "", api_key: str = ""):
        try:
            self.index_name = index_name or get_pinecone_index_name_eq()
            self.api_key = api_key or get_pinecone_api_key()
            self.pc = Pinecone(api_key=self.api_key)
            self.index = self.pc.Index(self.index_name)
            self.openai_client = OpenAI(api_key=get_openai_api_key())
        except Exception as error:
            raise CustomException(error, sys) from error

    def search(self, query: str, top_k: int = 2):
        try:
            embedding_response = self.openai_client.embeddings.create(
                input=query,
                model=OPENAI_EMBEDDING_MODEL,
                dimensions=OPENAI_EMBEDDING_DIMENSION,
            )
            if embedding_response is None:
                logging.error(f"Embedding response is None for query: {query}")
                raise ValueError(f"Embedding response is None for query: {query}")

            query_vector = embedding_response.data[0].embedding
            if query_vector is None:
                logging.error(f"Query vector is None for query: {query}")
                raise ValueError(f"Query vector is None for query: {query}")

            response = self.index.query(vector=query_vector, top_k=top_k, include_metadata=True)
            if response is None:
                logging.error(f"Response is None for query: {query}")
                raise ValueError(f"Response is None for query: {query}")

            results = []
            for match in response.matches:
                results.append({"id": match.id, "score": match.score, "metadata": match.metadata if match.metadata else {}})

            usage_info = None
            if hasattr(response, "usage") and response.usage:
                try:
                    usage_info = response.usage.to_dict() if hasattr(response.usage, "to_dict") else {
                        "read_units": getattr(response.usage, "read_units", None)
                    }
                except Exception:
                    usage_info = None

            return {
                "query": query,
                "matches": results,
                "namespace": response.namespace if hasattr(response, "namespace") else None,
                "usage": usage_info,
            }
        except Exception as error:
            raise CustomException(error, sys) from error
