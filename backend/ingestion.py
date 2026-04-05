import hashlib, tempfile, os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from db import get_vector_store, get_bm25_store
from session import SessionStore

sessions = SessionStore()
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120, separators=["\n\n", "\n", ". ", " ", ""])

async def ingest_pdf(content: bytes, session_id: str, filename: str) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        if not pages:
            raise ValueError("PDF contains no pages or cannot be read")
        for page in pages:
            page.metadata["source"] = filename
            page.metadata["session_id"] = session_id
        chunks = splitter.split_documents(pages)
        if not chunks:
            raise ValueError(f"PDF '{filename}' contains no extractable text")
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
    try:
        loader = WebBaseLoader(url, verify_ssl=False, requests_kwargs={"timeout": 20})
        docs = loader.load()
    except Exception as e:
        raise ValueError(f"Failed to fetch URL '{url}': {str(e)}")
    
    if not docs:
        raise ValueError(f"URL '{url}' contains no content")
    
    for doc in docs:
        doc.metadata["source"] = url
        doc.metadata["session_id"] = session_id
    chunks = splitter.split_documents(docs)
    if not chunks:
        raise ValueError(f"URL '{url}' contains no extractable text")
    url_id = hashlib.md5(url.encode()).hexdigest()[:8]
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{url_id}_{i}"
    get_vector_store(session_id).add_documents(chunks)
    get_bm25_store(session_id).add_documents(chunks)
    sessions.add_doc(session_id, {"name": url, "type": "url", "chunks": len(chunks)})
    return {"chunks": len(chunks)}
