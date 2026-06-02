#!/bin/bash
# Run once on the pod after provisioning.
# The RunPod pytorch image has CUDA and Docker pre-installed.
set -e

# Install Docker Compose plugin if not present
if ! docker compose version &>/dev/null; then
    apt-get update -q && apt-get install -y docker-compose-plugin
fi

# Pre-pull images so startup is fast during the workshop
docker pull vllm/vllm-openai:latest
docker pull prom/prometheus:latest
docker pull grafana/grafana:latest

echo ""
echo "Setup complete. Verify GPU:"
echo "  nvidia-smi"
