import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever

# Using FAISS instead of pgvector — no DB setup needed, runs in memory
_vector_stores = {}
_bm25_stores = {}
_bm25_docs = {}

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

def get_vector_store(session_id: str):
    if session_id not in _vector_stores:
        _vector_stores[session_id] = None
    return _VectorWrapper(session_id)

def get_bm25_store(session_id: str):
    if session_id not in _bm25_docs:
        _bm25_docs[session_id] = []
        _bm25_stores[session_id] = None
    return _BM25Wrapper(session_id)

class _VectorWrapper:
    def __init__(self, session_id):
        self.session_id = session_id

    def add_documents(self, docs):
        if not docs:
            return
        if _vector_stores[self.session_id] is None:
            _vector_stores[self.session_id] = FAISS.from_documents(docs, embeddings)
        else:
            _vector_stores[self.session_id].add_documents(docs)

    def similarity_search(self, query, k=6):
        store = _vector_stores.get(self.session_id)
        if store is None:
            return []
        return store.similarity_search(query, k=k)

class _BM25Wrapper:
    def __init__(self, session_id):
        self.session_id = session_id

    def add_documents(self, docs):
        if not docs:
            return
        _bm25_docs[self.session_id].extend(docs)
        if _bm25_docs[self.session_id]:  # Only create retriever if we have documents
            _bm25_stores[self.session_id] = BM25Retriever.from_documents(
                _bm25_docs[self.session_id], k=6
            )

    def get_relevant_documents(self, query, k=6):
        r = _bm25_stores.get(self.session_id)
        if r is None:
            return []
        r.k = k
        return r.get_relevant_documents(query)
