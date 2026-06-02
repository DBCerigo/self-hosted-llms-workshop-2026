# Self-Hosted LLMs: Running Your Own Inference Infrastructure

Workshop materials and server setup scripts for the hands-on session at [AI in Production 2026](https://ai-in-production.jumpingrivers.com/), 4 June 2026, Newcastle Upon Tyne.

> When does it make sense to run your own LLM inference infrastructure instead of paying per-token to third-party APIs? And once you've decided to — how do you actually do it?

The workshop covers the decision framework for third-party vs self-host, applies it to worked example LLM applications, then gets hands-on deploying inference servers using current leading open-source tooling.

Talk slides and further context: [datavaluepeople.com/blog/self-hosted-llms](https://datavaluepeople.com/blog/self-hosted-llms)

---

## What's in this repo

Two self-contained inference server stacks, each with provisioning, setup, and monitoring:

| Stack | Hardware | Purpose |
|---|---|---|
| `stacks/single-gpu/` | GCP g2-standard-4 + 1× L4 | Baseline single-GPU deployment |
| `stacks/multi-gpu/` | GCP g2-standard-24 + 2× L4 | Tensor-parallel multi-GPU deployment |

Shared monitoring stack (Prometheus + Grafana) in `monitoring/`.

---

## Stack structure

Each stack contains:

```
provision.sh      # create the server (RunPod pod or GCP VM)
setup.sh          # bootstraps the server: pre-pull Docker images
start_vllm.sh     # docker run vLLM — edit flags here to iterate on config
stop_vllm.sh      # stops the running vLLM container
```

Shared monitoring stack:

```
monitoring/start.sh   # docker compose up Prometheus + Grafana
```

The vLLM server exposes an OpenAI-compatible API on port 8000.
Prometheus scrapes metrics at `:8000/metrics`. Grafana dashboards on port 3000.

---

## Sending requests

`client.py` provides a simple wrapper around the OpenAI SDK pointed at the workshop server.

Set the server details first (shared at the session start):
```bash
export WORKSHOP_SERVER_URL=http://<server-ip>:8000/v1
export WORKSHOP_API_KEY=<api-key>
```

As a module:
```python
from client import chat
print(chat("Explain KV cache in one sentence"))
```

From the command line:
```bash
python client.py "Explain KV cache in one sentence"
```

---

## Prerequisites

- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- A HuggingFace token (for downloading models): `export HF_TOKEN=hf_...`
- The workshop API key (shared at the session start): `API_KEY=...`
