from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import uuid
import asyncio
from typing import Optional
from pydantic import BaseModel

from ingestion import ingest_pdf, ingest_url
from retrieval import hybrid_retrieve
from generation import stream_answer
from session import SessionStore

app = FastAPI(title="RAG Document Intelligence System", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
sessions = SessionStore()

class URLRequest(BaseModel):
    url: str
    session_id: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    session_id: str

@app.get("/")
async def root():
    return {"status": "ok", "message": "RAG Document Intelligence System"}

@app.post("/session/create")
async def create_session():
    session_id = str(uuid.uuid4())
    sessions.create(session_id)
    return {"session_id": session_id}

@app.post("/ingest/pdf")
async def ingest_pdf_endpoint(file: UploadFile = File(...), session_id: str = None):
    if not session_id:
        session_id = str(uuid.uuid4())
        sessions.create(session_id)
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    content = await file.read()
    result = await ingest_pdf(content, session_id, file.filename)
    return {"session_id": session_id, "filename": file.filename, "chunks_indexed": result["chunks"], "status": "success"}

@app.post("/ingest/url")
async def ingest_url_endpoint(request: URLRequest):
    session_id = request.session_id or str(uuid.uuid4())
    if not sessions.exists(session_id):
        sessions.create(session_id)
    result = await ingest_url(request.url, session_id)
    return {"session_id": session_id, "url": request.url, "chunks_indexed": result["chunks"], "status": "success"}

@app.get("/session/{session_id}/docs")
async def list_docs(session_id: str):
    if not sessions.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "documents": sessions.get_docs(session_id)}

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    if not sessions.exists(request.session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    chunks = await hybrid_retrieve(request.query, request.session_id)
    answer = await stream_answer(request.query, chunks, stream=False)
    return {"answer": answer, "sources": [c["source"] for c in chunks], "chunks_used": len(chunks)}

@app.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            session_id = data.get("session_id")
            query = data.get("query")
            if not session_id or not query:
                await websocket.send_json({"error": "session_id and query required"})
                continue
            if not sessions.exists(session_id):
                await websocket.send_json({"error": "Session not found"})
                continue
            chunks = await hybrid_retrieve(query, session_id)
            await websocket.send_json({"type": "sources", "sources": [c["source"] for c in chunks], "chunks_used": len(chunks)})
            async for token in stream_answer(query, chunks, stream=True):
                await websocket.send_json({"type": "token", "content": token})
                await asyncio.sleep(0)
            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
