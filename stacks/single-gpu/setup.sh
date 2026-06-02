#!/bin/bash
# Run once on the pod after provisioning.
# The RunPod pytorch image has CUDA and Docker pre-installed.
set -e

# Install Docker Compose plugin if not present
if ! docker compose version &>/dev/null; then
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# Pre-pull images so startup is fast during the workshop
docker pull vllm/vllm-openai:latest
docker pull prom/prometheus:latest
docker pull grafana/grafana:latest

echo ""
echo "Setup complete. Verify GPU:"
echo "  nvidia-smi"
