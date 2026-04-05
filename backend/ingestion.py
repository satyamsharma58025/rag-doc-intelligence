import hashlib, tempfile, os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from db import get_vector_store, get_bm25_store
from session import SessionStore

sessions = SessionStore()
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120, separators=["\n\n", "\n", ". ", " ", ""])

async def ingest_pdf(content: bytes, session_id: str, filename: str) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        for page in pages:
            page.metadata["source"] = filename
            page.metadata["session_id"] = session_id
        chunks = splitter.split_documents(pages)
        doc_id = hashlib.md5(content).hexdigest()[:8]
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = f"{doc_id}_{i}"
        get_vector_store(session_id).add_documents(chunks)
        get_bm25_store(session_id).add_documents(chunks)
        sessions.add_doc(session_id, {"name": filename, "type": "pdf", "chunks": len(chunks)})
        return {"chunks": len(chunks)}
    finally:
        os.unlink(tmp_path)

async def ingest_url(url: str, session_id: str) -> dict:
    loader = WebBaseLoader(url)
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = url
        doc.metadata["session_id"] = session_id
    chunks = splitter.split_documents(docs)
    url_id = hashlib.md5(url.encode()).hexdigest()[:8]
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{url_id}_{i}"
    get_vector_store(session_id).add_documents(chunks)
    get_bm25_store(session_id).add_documents(chunks)
    sessions.add_doc(session_id, {"name": url, "type": "url", "chunks": len(chunks)})
    return {"chunks": len(chunks)}
