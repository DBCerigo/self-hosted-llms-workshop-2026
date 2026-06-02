#!/bin/bash
# Run once on the VM after provisioning.
set -e

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# NVIDIA Container Toolkit — enables GPU passthrough into Docker
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update -q
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Pre-pull images so startup is fast during the workshop
sudo docker pull vllm/vllm-openai:latest
sudo docker pull prom/prometheus:latest
sudo docker pull grafana/grafana:latest

echo ""
echo "Setup complete. Log out and back in so docker group takes effect, then verify GPU:"
echo "  docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi"
