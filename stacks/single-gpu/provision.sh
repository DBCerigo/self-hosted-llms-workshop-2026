#!/bin/bash
# Creates a RunPod pod for the single-GPU stack.
# Prereq: runpodctl installed and authenticated (`runpodctl config --apiKey <YOUR_API_KEY>`)
# First time: add your SSH public key with `runpodctl ssh add-key --key-file <YOUR_SSH_KEY_FILE>`
set -e

runpodctl pod create \
    --name workshop-single-gpu \
    --gpu-id "NVIDIA RTX PRO 6000 Blackwell Server Edition" \
    --image "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04" \
    --container-disk-in-gb 50 \
    --volume-in-gb 100 \
    --volume-mount-path /workspace \
    --ports "8000/http,3000/http,9090/http,22/tcp"

echo ""
echo "Pod created. Get SSH details with:"
echo "  runpodctl pod list"
echo "  runpodctl ssh connect <pod-id>"
echo ""
echo "Then on the pod:"
echo "  cd /workspace && git clone https://github.com/DBCerigo/self-hosted-llms-workshop-2026 workshop"
echo "  cd workshop/stacks/single-gpu && bash setup.sh"
