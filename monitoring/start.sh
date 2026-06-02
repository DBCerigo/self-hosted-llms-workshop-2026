#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d

echo "Monitoring started."
echo "  Grafana:    https://${RUNPOD_POD_ID}-3000.proxy.runpod.net"
echo "  Prometheus: https://${RUNPOD_POD_ID}-9090.proxy.runpod.net"
