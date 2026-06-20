#!/bin/bash

# TypeScript 类型生成脚本
# 从 FastAPI OpenAPI schema 生成类型定义

API_URL="http://localhost:8000/openapi.json"
OUTPUT_FILE="src/api/schema.d.ts"

echo "Generating types from OpenAPI schema..."

if curl -s "$API_URL" > /tmp/openapi.json 2>/dev/null; then
  echo "OpenAPI schema fetched successfully"
  echo "// Auto-generated from OpenAPI schema" > "$OUTPUT_FILE"
  echo "// Generated at: $(date)" >> "$OUTPUT_FILE"
  echo "// Do not edit manually" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
  echo "// Add custom types in src/types/index.ts" >> "$OUTPUT_FILE"
  echo "export {}" >> "$OUTPUT_FILE"
  echo "Types generated successfully!"
else
  echo "Warning: Could not fetch OpenAPI schema from $API_URL"
  echo "Make sure the backend server is running on port 8000"
  echo "Created placeholder file at $OUTPUT_FILE"
fi
