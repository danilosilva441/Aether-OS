#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export AETHER_LLM_BACKEND=${AETHER_LLM_BACKEND:-mock}
export AETHER_MODEL=${AETHER_MODEL:-qwen2.5:3b}
export OLLAMA_URL=${OLLAMA_URL:-http://localhost:11434}
export AETHER_HOST=${AETHER_HOST:-0.0.0.0}
export AETHER_PORT=${AETHER_PORT:-8000}

python3 -m uvicorn main:app --host "$AETHER_HOST" --port "$AETHER_PORT"
