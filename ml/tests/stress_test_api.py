"""Simple API stress test for latency and throughput benchmarking."""

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "cardio_train.csv"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "results" / "api_stress_test.json"


def build_payload(df: pd.DataFrame, idx: int) -> dict:
    row = df.iloc[idx % len(df)]
    return {
        "id": int(row["id"]),
        "age": int(row["age"]),
        "gender": int(row["gender"]),
        "height": int(row["height"]),
        "weight": float(row["weight"]),
        "ap_hi": int(row["ap_hi"]),
        "ap_lo": int(row["ap_lo"]),
        "cholesterol": int(row["cholesterol"]),
        "gluc": int(row["gluc"]),
        "smoke": int(row["smoke"]),
        "alco": int(row["alco"]),
        "active": int(row["active"]),
    }


async def send_request(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    sem: asyncio.Semaphore,
    timeout_seconds: float,
):
    async with sem:
        start = time.perf_counter()
        try:
            resp = await client.post(url, json=payload, timeout=timeout_seconds)
            latency_ms = (time.perf_counter() - start) * 1000
            return resp.status_code, latency_ms
        except Exception:
            latency_ms = (time.perf_counter() - start) * 1000
            return 0, latency_ms


async def run_stress_test(base_url: str, total_requests: int, concurrency: int, timeout_seconds: float):
    df = pd.read_csv(DATA_PATH, sep=";")
    predict_url = f"{base_url.rstrip('/')}/predict"

    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        tasks = [
            send_request(client, predict_url, build_payload(df, i), sem, timeout_seconds)
            for i in range(total_requests)
        ]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

    latencies = [lat for _, lat in results]
    ok = sum(1 for status, _ in results if status == 200)

    metrics = {
        "base_url": base_url,
        "endpoint": "/predict",
        "total_requests": total_requests,
        "concurrency": concurrency,
        "timeout_seconds": timeout_seconds,
        "successful_requests": ok,
        "failed_requests": total_requests - ok,
        "success_rate": round(ok / total_requests, 4),
        "elapsed_seconds": round(elapsed, 3),
        "throughput_rps": round(total_requests / elapsed, 2),
        "latency_ms_avg": round(statistics.mean(latencies), 2),
        "latency_ms_p50": round(statistics.median(latencies), 2),
        "latency_ms_p95": round(sorted(latencies)[int(0.95 * len(latencies)) - 1], 2),
        "latency_ms_p99": round(sorted(latencies)[int(0.99 * len(latencies)) - 1], 2),
        "latency_ms_max": round(max(latencies), 2),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))
    print(f"\nSaved stress test report to: {OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stress test the heart disease API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--requests", type=int, default=500, help="Total number of requests")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrent requests")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds")
    args = parser.parse_args()

    asyncio.run(run_stress_test(args.base_url, args.requests, args.concurrency, args.timeout))
