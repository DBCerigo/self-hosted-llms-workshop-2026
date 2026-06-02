#!/bin/bash
set -e

PROJECT=$(gcloud config get-value project)
ZONE="europe-west4-a"
INSTANCE_NAME="workshop-multi-gpu"

echo "Creating VM in project: $PROJECT"

gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT \
    --zone=$ZONE \
    --machine-type=g2-standard-24 \
    --image-family=common-cu129-ubuntu-2204-nvidia-580 \
    --image-project=deeplearning-platform-release \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-ssd \
    --maintenance-policy=TERMINATE \
    --tags=vllm-workshop

# g2-standard-24 includes 2× L4 GPUs — no separate --accelerator flag needed

gcloud compute firewall-rules create allow-vllm-workshop \
    --allow=tcp:8000,tcp:3000,tcp:9090 \
    --target-tags=vllm-workshop \
    --description="vLLM API (8000), Grafana (3000), Prometheus (9090)" \
    2>/dev/null || true

echo ""
echo "VM ready. SSH in and run setup.sh:"
echo "  gcloud compute scp --zone=$ZONE --recurse ../../ $INSTANCE_NAME:~/workshop"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo "  cd ~/workshop/stacks/multi-gpu && bash setup.sh"
