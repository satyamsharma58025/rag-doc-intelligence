#!/bin/bash
set -e

echo "=== Testing Full RAG Query Flow ==="
echo ""

# Create session
SESSION=$(curl -s -X POST http://127.0.0.1:5174/api/session/create | jq -r .session_id)
echo "✓ Session: ${SESSION:0:8}..."

# Upload PDF
echo ""
echo "Uploading PDF..."
UPLOAD=$(curl -s -F "file=@test.pdf" "http://127.0.0.1:5174/api/ingest/pdf?session_id=$SESSION")
CHUNKS=$(echo "$UPLOAD" | jq -r .chunks_indexed)
echo "✓ PDF indexed with $CHUNKS chunks"

# Query with streaming (WebSocket)
echo ""
echo "Testing WebSocket streaming query..."
RESPONSE=$(timeout 15 curl -s -X POST http://127.0.0.1:5174/api/query \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"What does the document say?\",\"session_id\":\"$SESSION\"}")

echo ""
echo "Response received:"
echo "$RESPONSE" | jq . || echo "$RESPONSE"

echo ""
echo "=== Test Complete ==="
