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

Shared monitoring stack (Prometheus + Grafana) in `monitoring/`. Use Chrome to view Grafana dashboards — Firefox has known issues with certain Grafana fetch patterns.

---

## Stack structure

Each stack contains:

```
provision.sh      # create the GCP VM
setup.sh          # bootstraps the server: install Docker, pre-pull images
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

Set the server details first (shared at the session start):
```bash
export WORKSHOP_SERVER_URL=http://<server-ip>:8000/v1
export WORKSHOP_API_KEY=<api-key>
```

`client.py` is a simple wrapper around the OpenAI SDK:

```python
from client import chat
print(chat("Explain KV cache in one sentence"))
```

```bash
python client.py "Explain KV cache in one sentence"
```

---

## Profiling

`profiling/profile.py` generates realistic load against the server so metrics appear in Grafana. It requires only `openai` (already needed for `client.py`).

```bash
python profiling/profile.py [scenario]
```

| Scenario | What it does |
|---|---|
| `baseline` | Moderate steady load — good starting point |
| `high-concurrency` | High request rate — stresses KV cache |
| `long-prompts` | Long inputs — increases TTFT and memory pressure |
| `throughput` | All requests at once — finds the throughput ceiling |
| `saturation` | Steady stream above server capacity — use this to demonstrate `--max-num-seqs` |
| `doctor` | Long system prompt + short questions — demonstrates prefix caching |

### Hands-on loop

The core workshop exercise is: **observe → hypothesise → change → re-profile → verify**.

A good first demo: run `saturation`, then edit `--max-num-seqs` in `start_vllm.sh` (try `8` instead of `64`), restart the server, run `saturation` again, and watch TTFT in Grafana.

```bash
# 1. Profile with current config
python profiling/profile.py saturation

# 2. Edit --max-num-seqs in stacks/single-gpu/start_vllm.sh, then:
bash stacks/single-gpu/stop_vllm.sh
bash stacks/single-gpu/start_vllm.sh

# 3. Re-profile and compare Grafana
python profiling/profile.py saturation
```

---

## Prerequisites

- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- HuggingFace token for model downloads: `export HF_TOKEN=hf_...`
- Server URL and API key (shared at the session start):
  ```bash
  export WORKSHOP_SERVER_URL=http://<server-ip>:8000/v1
  export WORKSHOP_API_KEY=<api-key>
  ```
