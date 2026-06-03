#!/usr/bin/env python3
"""Load profiler for the workshop hands-on section.

Usage:
    python profile.py [scenario]

Scenarios:
    baseline         (default) moderate load, typical prompt lengths
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

SCENARIOS = {
    "baseline":         dict(input_tokens=256,  output_tokens=128, num_prompts=60,  request_rate=4.0),
    "high-concurrency": dict(input_tokens=256,  output_tokens=128, num_prompts=100, request_rate=20.0),
    "long-prompts":     dict(input_tokens=2048, output_tokens=256, num_prompts=30,  request_rate=2.0),
    "throughput":       dict(input_tokens=128,  output_tokens=128, num_prompts=200, request_rate=None),
}

_WORDS = (
    "the quick brown fox jumps over a lazy dog and cat sat on mat with some more random words here "
    "machine learning model inference latency throughput token cache memory gpu batch size context "
    "neural network attention head layer weight gradient optimizer loss function training data"
).split()


def _make_prompt(approx_tokens: int) -> str:
    """Generate a prompt of approximately the given token length (~0.75 words/token)."""
    return " ".join(random.choices(_WORDS, k=int(approx_tokens * 0.75)))


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
    print(f"Input tokens: ~{cfg['input_tokens']}  |  Output tokens: ~{cfg['output_tokens']}")
    print(f"Requests:     {cfg['num_prompts']} at {rate_str}")
    print()
    print("Open Grafana and watch TTFT, throughput, and KV cache utilisation.")
    print()

    prompts = [_make_prompt(cfg["input_tokens"]) for _ in range(cfg["num_prompts"])]
    results: list[_Result] = []
    start_all = time.perf_counter()

    try:
        if cfg["request_rate"] is None:
            tasks = [_send_request(client, model, p, cfg["output_tokens"]) for p in prompts]
            results = list(await asyncio.gather(*tasks))
        else:
            interval = 1.0 / cfg["request_rate"]
            tasks = []
            for i, prompt in enumerate(prompts):
                tasks.append(asyncio.create_task(
                    _send_request(client, model, prompt, cfg["output_tokens"])
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
