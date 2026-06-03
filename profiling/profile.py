#!/usr/bin/env python3
"""Load profiler for the workshop hands-on section.

Usage:
    python profile.py [scenario]

Scenarios:
    baseline         (default) moderate load, mixed prompt lengths
    high-concurrency spike in concurrent requests — stresses KV cache
    long-prompts     long inputs — increases TTFT and memory pressure
    throughput       fire everything at once — find the throughput ceiling

Requires: pip install openai
"""
import asyncio
import os
import random
import sys
import time
from dataclasses import dataclass

from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# Prompt sets
# ---------------------------------------------------------------------------

_MIXED_PROMPTS = [
    # Short
    "What does HTTP stand for?",
    "In one sentence, what is a transformer model?",
    "What is the difference between RAM and storage?",
    "What year was Python first released?",
    "What is a Docker container?",
    # Medium
    "Explain what a REST API is and when you would use one.",
    "What is the difference between supervised and unsupervised learning?",
    "How does garbage collection work in Python?",
    "Explain the CAP theorem in distributed systems.",
    "Explain what a GPU does differently from a CPU and why it matters for ML.",
    "What is the difference between TCP and UDP? Give an example use case for each.",
    "What is the difference between a process and a thread?",
    # Longer
    "Write a Python function that implements binary search. Include type hints and a docstring.",
    "Explain how the attention mechanism works in transformer models, step by step.",
    "What are the trade-offs between using a relational database and a document store? Give examples of when you would choose each.",
    "Write a Python class for a thread-safe LRU cache with get and put methods.",
    "Explain the difference between batch normalisation and layer normalisation, and when you would use each.",
    "How does vLLM's PagedAttention improve GPU memory efficiency compared to naive KV cache management?",
    "Describe the steps involved in fine-tuning a pre-trained language model: what data you need, what can go wrong, and how you evaluate success.",
    "Write a SQL query to find the top 5 customers by total revenue across all orders, handling NULLs correctly. Explain each part.",
]

# Long inputs: a substantial context preamble forces a large KV cache per request,
# stressing TTFT and memory even at low concurrency.
_LONG_CONTEXT_PREAMBLE = """\
Background — LLM Inference Fundamentals:

The KV cache stores the key and value tensors computed during the forward pass for \
each token in the context. Because these tensors are reused by subsequent tokens via \
the attention mechanism, caching them avoids redundant computation. However, the \
memory required grows linearly with both sequence length and batch size, so managing \
it efficiently is a central challenge in inference serving.

PagedAttention (introduced by vLLM) draws on virtual-memory paging: instead of \
allocating one large contiguous block per sequence, it divides the KV cache into \
fixed-size blocks that can be placed non-contiguously in GPU memory. This eliminates \
fragmentation and enables near-zero memory waste, allowing the GPU to hold far more \
concurrent sequences than a naïve allocator.

Continuous batching (iteration-level scheduling) keeps the GPU busy by processing \
one decoding step across all active sequences per iteration and immediately inserting \
newly arrived requests into free slots. Static batching, by contrast, waits for a \
full batch before starting and idles the GPU while shorter sequences in the batch \
finish. The difference in GPU utilisation at variable load can be substantial.

Tensor parallelism splits weight matrices across multiple GPUs so each holds a shard; \
an all-reduce synchronises activations after each layer. This reduces per-GPU memory \
and latency but adds communication overhead. Pipeline parallelism assigns consecutive \
layers to different GPUs, which can increase throughput via micro-batching but \
introduces pipeline-bubble latency.

Quantisation lowers weight precision from FP16/BF16 to INT8 or INT4, shrinking model \
size and often increasing throughput at a small quality cost. AWQ (Activation-aware \
Weight Quantisation) preserves the weights most influential to activations at full \
precision, achieving better quality than naive rounding at the same bit-width.\
"""

_LONG_CONTEXT_PROMPTS = [
    _LONG_CONTEXT_PREAMBLE + "\n\nQuestion: What is the KV cache and why does its size matter for inference performance? Answer in detail.",
    _LONG_CONTEXT_PREAMBLE + "\n\nQuestion: Compare tensor parallelism and pipeline parallelism. When would you choose each?",
    _LONG_CONTEXT_PREAMBLE + "\n\nQuestion: How does PagedAttention work and what specific problem does it solve over a naïve allocator?",
    _LONG_CONTEXT_PREAMBLE + "\n\nQuestion: What are the trade-offs of quantisation for LLM inference? When does quality degrade noticeably?",
    _LONG_CONTEXT_PREAMBLE + "\n\nQuestion: Explain continuous batching and why it improves GPU utilisation compared to static batching.",
]

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS = {
    "baseline":         dict(prompt_set="mixed",        num_prompts=50,  request_rate=4.0,  max_tokens=512),
    "high-concurrency": dict(prompt_set="mixed",        num_prompts=80,  request_rate=20.0, max_tokens=512),
    "long-prompts":     dict(prompt_set="long_context", num_prompts=20,  request_rate=1.0,  max_tokens=512),
    "throughput":       dict(prompt_set="mixed",        num_prompts=100, request_rate=None, max_tokens=512),
}

_PROMPT_SETS = {
    "mixed":        _MIXED_PROMPTS,
    "long_context": _LONG_CONTEXT_PROMPTS,
}

# ---------------------------------------------------------------------------
# Core async machinery
# ---------------------------------------------------------------------------

@dataclass
class _Result:
    ttft_ms: float
    total_ms: float
    output_tokens: int
    success: bool


async def _send_request(
    client: AsyncOpenAI, model: str, prompt: str, max_tokens: int
) -> _Result:
    start = time.perf_counter()
    ttft_ms = None
    output_tokens = 0
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - start) * 1000
            if chunk.choices and chunk.choices[0].delta.content:
                output_tokens += 1
        total_ms = (time.perf_counter() - start) * 1000
        return _Result(ttft_ms or total_ms, total_ms, output_tokens, True)
    except Exception as exc:
        print(f"  request failed: {exc}", file=sys.stderr)
        return _Result(0.0, (time.perf_counter() - start) * 1000, 0, False)


def _percentile(sorted_vals: list[float], pct: float) -> float:
    idx = min(int(len(sorted_vals) * pct / 100), len(sorted_vals) - 1)
    return sorted_vals[idx]


async def _run(scenario: str) -> None:
    cfg = SCENARIOS[scenario]
    server_url = os.environ["WORKSHOP_SERVER_URL"]
    api_key = os.environ["WORKSHOP_API_KEY"]
    model = os.environ.get("WORKSHOP_MODEL", "Qwen/Qwen2.5-7B-Instruct-AWQ")

    client = AsyncOpenAI(base_url=server_url, api_key=api_key)
    rate_str = f"{cfg['request_rate']} req/s" if cfg["request_rate"] else "all at once"

    print(f"Scenario:     {scenario}")
    print(f"Server:       {server_url}")
    print(f"Model:        {model}")
    print(f"Requests:     {cfg['num_prompts']} at {rate_str}  |  max_tokens={cfg['max_tokens']}")
    print()
    print("Open Grafana and watch TTFT, throughput, and KV cache utilisation.")
    print()

    pool = _PROMPT_SETS[cfg["prompt_set"]]
    prompts = [random.choice(pool) for _ in range(cfg["num_prompts"])]
    results: list[_Result] = []
    start_all = time.perf_counter()

    try:
        if cfg["request_rate"] is None:
            tasks = [_send_request(client, model, p, cfg["max_tokens"]) for p in prompts]
            results = list(await asyncio.gather(*tasks))
        else:
            interval = 1.0 / cfg["request_rate"]
            tasks = []
            for i, prompt in enumerate(prompts):
                tasks.append(asyncio.create_task(
                    _send_request(client, model, prompt, cfg["max_tokens"])
                ))
                print(f"  sent {i + 1}/{cfg['num_prompts']}", end="\r")
                if i < len(prompts) - 1:
                    await asyncio.sleep(interval)
            results = list(await asyncio.gather(*tasks))
    except asyncio.CancelledError:
        pass

    duration = time.perf_counter() - start_all
    successes = [r for r in results if r.success]

    if not successes:
        print("\nAll requests failed.")
        return

    ttfts = sorted(r.ttft_ms for r in successes)
    e2els = sorted(r.total_ms for r in successes)
    total_output = sum(r.output_tokens for r in successes)

    print(f"\n{'=' * 52}")
    print(f"Completed:    {len(successes)}/{len(results)} requests in {duration:.1f}s")
    print(f"Throughput:   {len(successes) / duration:.1f} req/s  |  {total_output / duration:.0f} output tok/s")
    print(f"TTFT (ms):    mean={sum(ttfts)/len(ttfts):.0f}  p50={_percentile(ttfts,50):.0f}  p95={_percentile(ttfts,95):.0f}  p99={_percentile(ttfts,99):.0f}")
    print(f"E2E lat (ms): mean={sum(e2els)/len(e2els):.0f}  p50={_percentile(e2els,50):.0f}  p95={_percentile(e2els,95):.0f}  p99={_percentile(e2els,99):.0f}")
    print(f"{'=' * 52}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    scenario = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if scenario not in SCENARIOS:
        print(f"Unknown scenario: {scenario}")
        print(f"Available: {', '.join(SCENARIOS)}")
        sys.exit(1)

    for var in ("WORKSHOP_SERVER_URL", "WORKSHOP_API_KEY"):
        if not os.environ.get(var):
            print(f"Error: {var} is not set")
            sys.exit(1)

    try:
        asyncio.run(_run(scenario))
    except KeyboardInterrupt:
        print("\nInterrupted.")
