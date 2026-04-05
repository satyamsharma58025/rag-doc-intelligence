import os
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import BM25Retriever

_bm25_stores = {}
_bm25_docs = {}

POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:password@localhost:5432/ragdb")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def get_vector_store(session_id: str) -> PGVector:
    return PGVector(
        embeddings=embeddings,
        collection_name=f"session_{session_id.replace('-','_')}",
        connection=POSTGRES_URL,
        use_jsonb=True,
    )

def get_bm25_store(session_id: str):
    if session_id not in _bm25_docs:
        _bm25_docs[session_id] = []
        _bm25_stores[session_id] = None
    return _BM25Wrapper(session_id)

class _BM25Wrapper:
    def __init__(self, session_id):
        self.session_id = session_id
    def add_documents(self, docs):
        _bm25_docs[self.session_id].extend(docs)
        _bm25_stores[self.session_id] = BM25Retriever.from_documents(_bm25_docs[self.session_id], k=6)
    def get_relevant_documents(self, query, k=6):
        r = _bm25_stores.get(self.session_id)
        if r is None:
            return []
        r.k = k
        return r.get_relevant_documents(query)
