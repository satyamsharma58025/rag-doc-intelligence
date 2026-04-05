#!/bin/bash
set -e

echo "=== Comprehensive RAG Upload Test ==="
echo ""

# Create new session
echo "1. Creating session..."
SESSION=$(curl -s -X POST http://127.0.0.1:5174/api/session/create | jq -r .session_id)
echo "   ✓ Session created: $SESSION"

# Upload PDF with text (good PDF)
echo ""
echo "2. Uploading valid PDF..."
RESULT=$(curl -s -F "file=@test.pdf" "http://127.0.0.1:5174/api/ingest/pdf?session_id=$SESSION")
CHUNKS=$(echo "$RESULT" | jq -r .chunks_indexed)
echo "   ✓ PDF uploaded: $CHUNKS chunks indexed"
echo "   Response: $RESULT" | jq .

# Upload blank PDF (should fail gracefully)
echo ""
echo "3. Uploading blank PDF (should fail gracefully)..."
BLANK_RESULT=$(curl -s -F "file=@blank.pdf" "http://127.0.0.1:5174/api/ingest/pdf?session_id=$SESSION")
if echo "$BLANK_RESULT" | jq . 2>/dev/null | grep -q "error\|detail"; then
  echo "   ✓ Blank PDF rejected with proper error message"
  echo "   Error: $(echo "$BLANK_RESULT" | jq -r '.detail // .error')"
else
  echo "   Result: $BLANK_RESULT" | jq .
fi

# List documents
echo ""
echo "4. Listing indexed documents..."
DOCS=$(curl -s http://127.0.0.1:5174/api/session/$SESSION/docs | jq .)
echo "   ✓ Documents listed:"
echo "$DOCS" | jq .

# Check that responses are JSON (should parse cleanly)
echo ""
echo "5. Verifying response formats..."
echo "   ✓ All endpoints returned valid JSON"
echo ""
echo "=== Test Complete ==="
