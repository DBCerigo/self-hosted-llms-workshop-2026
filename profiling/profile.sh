#!/bin/bash
# Generate load against the vLLM server so metrics appear in Grafana.
# Watch the Grafana dashboard while this runs.
#
# Requires: pip install vllm
# Usage:    ./profile.sh [scenario]
#
# Scenarios:
#   baseline         (default) moderate load, typical prompt lengths
#   high-concurrency spike in concurrent requests — stresses KV cache
#   long-prompts     long inputs — increases TTFT and memory pressure
#   throughput       fire everything at once — find the throughput ceiling

set -e

: "${WORKSHOP_SERVER_URL:?export WORKSHOP_SERVER_URL=http://<ip>:8000/v1}"
: "${WORKSHOP_API_KEY:?export WORKSHOP_API_KEY=<key>}"

# vllm bench serve uses OPENAI_API_KEY for the Authorization header
export OPENAI_API_KEY="$WORKSHOP_API_KEY"

# Strip trailing /v1 if present — bench serve wants the base URL
BASE_URL="${WORKSHOP_SERVER_URL%/v1}"

MODEL="${WORKSHOP_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
SCENARIO="${1:-baseline}"

case "$SCENARIO" in
    baseline)
        INPUT_LEN=256
        OUTPUT_LEN=128
        NUM_PROMPTS=60
        REQUEST_RATE=4
        ;;
    high-concurrency)
        INPUT_LEN=256
        OUTPUT_LEN=128
        NUM_PROMPTS=100
        REQUEST_RATE=20
        ;;
    long-prompts)
        INPUT_LEN=2048
        OUTPUT_LEN=256
        NUM_PROMPTS=30
        REQUEST_RATE=2
        ;;
    throughput)
        INPUT_LEN=128
        OUTPUT_LEN=128
        NUM_PROMPTS=200
        REQUEST_RATE=inf
        ;;
    *)
        echo "Unknown scenario: $SCENARIO"
        echo "Available: baseline, high-concurrency, long-prompts, throughput"
        exit 1
        ;;
esac

echo "Scenario:     $SCENARIO"
echo "Server:       $BASE_URL"
echo "Model:        $MODEL"
echo "Input tokens: ~$INPUT_LEN  |  Output tokens: ~$OUTPUT_LEN"
echo "Requests:     $NUM_PROMPTS at ${REQUEST_RATE} req/s"
echo ""
echo "Open Grafana and watch TTFT, throughput, and KV cache utilisation."
echo ""

vllm bench serve \
    --base-url "$BASE_URL" \
    --model "$MODEL" \
    --dataset-name random \
    --random-input-len "$INPUT_LEN" \
    --random-output-len "$OUTPUT_LEN" \
    --num-prompts "$NUM_PROMPTS" \
    --request-rate "$REQUEST_RATE"
