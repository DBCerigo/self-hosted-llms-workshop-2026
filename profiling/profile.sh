#!/bin/bash
# Generate load against the vLLM server so metrics appear in Grafana.
# Watch the Grafana dashboard while this runs.
#
# Requires: pip install vllm
# Usage:    ./profile.sh [scenario]
#
# Scenarios:
#   baseline         (default) moderate load, realistic conversation prompts
#   high-concurrency spike in concurrent requests — stresses KV cache
#   throughput       fire everything at once — find the throughput ceiling

set -e

: "${WORKSHOP_SERVER_URL:?export WORKSHOP_SERVER_URL=http://<ip>:8000/v1}"
: "${WORKSHOP_API_KEY:?export WORKSHOP_API_KEY=<key>}"

# vllm bench serve reads the API key from OPENAI_API_KEY
export OPENAI_API_KEY="$WORKSHOP_API_KEY"

# Strip trailing /v1 if present — bench serve wants the base URL
BASE_URL="${WORKSHOP_SERVER_URL%/v1}"

MODEL="${WORKSHOP_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
SCENARIO="${1:-baseline}"

case "$SCENARIO" in
    baseline)
        NUM_PROMPTS=50
        REQUEST_RATE=4
        ;;
    high-concurrency)
        NUM_PROMPTS=80
        REQUEST_RATE=20
        ;;
    throughput)
        NUM_PROMPTS=100
        REQUEST_RATE=inf
        ;;
    *)
        echo "Unknown scenario: $SCENARIO"
        echo "Available: baseline, high-concurrency, throughput"
        exit 1
        ;;
esac

echo "Scenario:     $SCENARIO"
echo "Server:       $BASE_URL"
echo "Model:        $MODEL"
echo "Requests:     $NUM_PROMPTS at ${REQUEST_RATE} req/s  (ShareGPT dataset)"
echo ""
echo "Open Grafana and watch TTFT, throughput, and KV cache utilisation."
echo ""

vllm bench serve \
    --base-url "$BASE_URL" \
    --model "$MODEL" \
    --dataset-name sharegpt \
    --num-prompts "$NUM_PROMPTS" \
    --request-rate "$REQUEST_RATE"
