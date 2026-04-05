import { useState, useRef, useEffect, useCallback } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS  = API.replace("http", "ws");

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [docs, setDocs]           = useState([]);
  const [messages, setMessages]   = useState([]);
  const [query, setQuery]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus]       = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/session/create`, { method: "POST" })
      .then(r => r.json()).then(d => setSessionId(d.session_id));
  }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const uploadPDF = async (file) => {
    setUploading(true); setStatus(`Ingesting ${file.name}…`);
    const form = new FormData();
    form.append("file", file);
    try {
      const res  = await fetch(`${API}/ingest/pdf?session_id=${sessionId}`, { method: "POST", body: form });
      const data = await res.json();
      setDocs(d => [...d, { name: file.name, chunks: data.chunks_indexed, type: "pdf" }]);
      setStatus(`✓ ${file.name} — ${data.chunks_indexed} chunks indexed`);
    } catch { setStatus("Upload failed."); }
    finally { setUploading(false); }
  };

  const uploadURL = async (url) => {
    setUploading(true); setStatus(`Fetching ${url}…`);
    try {
      const res  = await fetch(`${API}/ingest/url`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url, session_id: sessionId }) });
      const data = await res.json();
      setDocs(d => [...d, { name: url, chunks: data.chunks_indexed, type: "url" }]);
      setStatus(`✓ URL indexed — ${data.chunks_indexed} chunks`);
    } catch { setStatus("URL ingestion failed."); }
    finally { setUploading(false); }
  };

  const sendQuery = useCallback(() => {
    if (!query.trim() || !sessionId || loading) return;
    const q = query.trim(); setQuery(""); setLoading(true);
    setMessages(m => [...m, { role: "user", content: q }, { role: "assistant", content: "", sources: [], streaming: true }]);
    const ws = new WebSocket(`${WS}/ws/query`);
    ws.onopen = () => ws.send(JSON.stringify({ session_id: sessionId, query: q }));
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "sources") {
        setMessages(m => { const u = [...m]; u[u.length-1].sources = data.sources; return u; });
      } else if (data.type === "token") {
        setMessages(m => { const u = [...m]; u[u.length-1].content += data.content; return u; });
      } else if (data.type === "done") {
        setMessages(m => { const u = [...m]; u[u.length-1].streaming = false; return u; });
        setLoading(false); ws.close();
      } else if (data.type === "error") {
        setMessages(m => { const u = [...m]; u[u.length-1].content = `Error: ${data.message}`; u[u.length-1].streaming = false; return u; });
        setLoading(false); ws.close();
      }
    };
    ws.onerror = () => { setLoading(false); setStatus("WebSocket error."); };
  }, [query, sessionId, loading]);

  const onKeyDown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendQuery(); } };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="logo">📄 DocIntel</span>
          <span className="version">RAG System</span>
        </div>
        <div className="upload-section">
          <p className="section-label">Upload PDF</p>
          <label className="upload-btn">
            {uploading ? "Processing…" : "+ Add PDF"}
            <input type="file" accept=".pdf" hidden onChange={e => e.target.files[0] && uploadPDF(e.target.files[0])} />
          </label>
        </div>
        <div className="upload-section">
          <p className="section-label">Add URL</p>
          <form onSubmit={e => { e.preventDefault(); uploadURL(e.target.url.value); e.target.reset(); }}>
            <input name="url" type="url" placeholder="https://example.com" className="url-input" />
            <button type="submit" className="upload-btn" disabled={uploading}>Fetch</button>
          </form>
        </div>
        {docs.length > 0 && (
          <div className="docs-list">
            <p className="section-label">Indexed Documents</p>
            {docs.map((d, i) => (
              <div key={i} className="doc-item">
                <span className="doc-icon">{d.type === "pdf" ? "📕" : "🌐"}</span>
                <div className="doc-info">
                  <span className="doc-name">{d.name.length > 28 ? d.name.slice(0,28)+"…" : d.name}</span>
                  <span className="doc-chunks">{d.chunks} chunks</span>
                </div>
              </div>
            ))}
          </div>
        )}
        {status && <div className="status-bar">{status}</div>}
        <div className="session-info">
          <span className="section-label">Session</span>
          <code className="session-id">{sessionId?.slice(0,8)}…</code>
        </div>
      </aside>
      <main className="chat-area">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <h2>Upload a document, then ask anything.</h2>
              <p>Powered by hybrid RAG: dense (pgvector) + sparse (BM25) with GPT-4o.</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="message-bubble">
                {msg.content || (msg.streaming ? <span className="cursor">▋</span> : "")}
                {msg.streaming && msg.content && <span className="cursor">▋</span>}
              </div>
              {msg.role === "assistant" && msg.sources?.length > 0 && (
                <div className="sources">
                  {[...new Set(msg.sources)].map((s, j) => (
                    <span key={j} className="source-tag">📎 {s.length > 40 ? s.slice(0,40)+"…" : s}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="input-row">
          <textarea value={query} onChange={e => setQuery(e.target.value)} onKeyDown={onKeyDown}
            placeholder={docs.length === 0 ? "Upload a document first…" : "Ask anything about your documents…"}
            disabled={loading || docs.length === 0} rows={2} />
          <button onClick={sendQuery} disabled={loading || !query.trim() || docs.length === 0} className="send-btn">
            {loading ? "…" : "↑"}
          </button>
        </div>
      </main>
    </div>
  );
}
