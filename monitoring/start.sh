#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d

echo "Monitoring started."
echo "  Grafana:    http://$(curl -s ifconfig.me):3000"
echo "  Prometheus: http://$(curl -s ifconfig.me):9090"
