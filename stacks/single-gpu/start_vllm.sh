#!/bin/bash
# Edit the vLLM flags below, then run this script to (re)start the server.
# Full flag reference: https://docs.vllm.ai/en/latest/configuration/engine_args/
set -e

: "${HF_TOKEN:?HF_TOKEN is not set}"
: "${API_KEY:?API_KEY is not set}"

docker run -d \
    --name vllm \
    --gpus all \
    --network host \
    --ipc=host \
    -v /opt/hf-cache:/root/.cache/huggingface \
    -e HUGGING_FACE_HUB_TOKEN=$HF_TOKEN \
    vllm/vllm-openai:latest \
        --model Qwen/Qwen2.5-7B-Instruct-AWQ \
        --quantization awq \
        --max-model-len 8192 \
        --max-num-seqs 64 \
        --gpu-memory-utilization 0.90 \
        --kv-cache-dtype auto \
        --api-key $API_KEY

echo "vLLM starting — follow logs with: docker logs vllm -f"
echo "API will be ready at http://$(curl -s ifconfig.me):8000/v1"
