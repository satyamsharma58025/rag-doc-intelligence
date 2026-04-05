from typing import List, Dict
from db import get_vector_store, get_bm25_store

TOP_K = 6
RRF_K = 60
FINAL_K = 5

def reciprocal_rank_fusion(dense_results, sparse_results, k=RRF_K):
    scores = {}
    docs_map = {}
    for rank, doc in enumerate(dense_results):
        cid = doc.metadata.get("chunk_id", doc.page_content[:40])
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        docs_map[cid] = {"content": doc.page_content, "source": doc.metadata.get("source", "unknown"), "chunk_id": cid}
    for rank, doc in enumerate(sparse_results):
        cid = doc.metadata.get("chunk_id", doc.page_content[:40])
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        if cid not in docs_map:
            docs_map[cid] = {"content": doc.page_content, "source": doc.metadata.get("source", "unknown"), "chunk_id": cid}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [docs_map[cid] for cid, _ in ranked[:FINAL_K]]

async def hybrid_retrieve(query: str, session_id: str) -> List[Dict]:
    dense_docs = get_vector_store(session_id).similarity_search(query, k=TOP_K)
    sparse_docs = get_bm25_store(session_id).get_relevant_documents(query, k=TOP_K)
    return reciprocal_rank_fusion(dense_docs, sparse_docs)
