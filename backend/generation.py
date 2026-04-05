from typing import List, Dict, AsyncGenerator, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

SYSTEM_PROMPT = """You are a precise document analysis assistant.
Answer only from the provided context. If the answer is not in the context, say: "I couldn't find relevant information in the uploaded documents."
Cite the source document when referencing specific information. Be concise and factual."""

def build_context(chunks):
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Chunk {i} | Source: {chunk.get('source','unknown')}]\n{chunk.get('content','')}")
    return "\n\n---\n\n".join(parts)

async def stream_answer(query: str, chunks: List[Dict], stream: bool = True) -> Union[AsyncGenerator, str]:
    context = build_context(chunks)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n\n{context}\n\n---\n\nQuestion: {query}\n\nAnswer:")
    ]
    if stream:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0, streaming=True)
        async def token_generator():
            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield chunk.content
        return token_generator()
    else:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0)
        response = await llm.ainvoke(messages)
        return response.content
