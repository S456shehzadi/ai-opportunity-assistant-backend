"""Production Load Testing Script.

Simulates concurrent user load against the AI Opportunity Assistant API.
Measures throughput, error rates, and p50 / p95 / p99 latencies.
"""

import argparse
import asyncio
import statistics
import time
from typing import Any

import httpx


async def worker(
    client: httpx.AsyncClient,
    base_url: str,
    endpoint: str,
    duration_secs: float,
    latencies: list[float],
    errors: list[str],
) -> None:
    start_time = time.monotonic()
    url = f"{base_url.rstrip('/')}{endpoint}"

    while time.monotonic() - start_time < duration_secs:
        req_start = time.monotonic()
        try:
            resp = await client.get(url, timeout=5.0)
            latency = (time.monotonic() - req_start) * 1000.0  # ms
            if resp.status_code < 400:
                latencies.append(latency)
            else:
                errors.append(f"HTTP {resp.status_code}")
        except Exception as e:
            errors.append(str(e))


async def run_load_test(
    base_url: str,
    endpoint: str,
    concurrency: int,
    duration_secs: float,
) -> dict[str, Any]:
    print("--- Starting Load Test ---")
    print(f"Target URL:    {base_url}{endpoint}")
    print(f"Concurrency:   {concurrency} workers")
    print(f"Duration:      {duration_secs}s\n")

    latencies: list[float] = []
    errors: list[str] = []

    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency * 2)
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [
            asyncio.create_task(
                worker(client, base_url, endpoint, duration_secs, latencies, errors)
            )
            for _ in range(concurrency)
        ]
        await asyncio.gather(*tasks)

    total_requests = len(latencies) + len(errors)
    rps = total_requests / duration_secs if duration_secs > 0 else 0

    results: dict[str, Any] = {
        "total_requests": total_requests,
        "successful_requests": len(latencies),
        "failed_requests": len(errors),
        "requests_per_second": round(rps, 2),
        "p50_ms": round(statistics.median(latencies), 2) if latencies else 0,
        "p95_ms": round(statistics.quantiles(latencies, n=20)[18], 2)
        if len(latencies) >= 20
        else 0,
        "p99_ms": round(statistics.quantiles(latencies, n=100)[98], 2)
        if len(latencies) >= 100
        else 0,
        "max_ms": round(max(latencies), 2) if latencies else 0,
        "min_ms": round(min(latencies), 2) if latencies else 0,
    }

    print("--- Load Test Results ---")
    print(f"Total Requests:      {results['total_requests']}")
    print(
        f"Success Rate:        {len(latencies) / total_requests * 100:.1f}%"
        if total_requests
        else "0%"
    )
    print(f"Throughput (RPS):    {results['requests_per_second']}")
    print(f"Latency P50:         {results['p50_ms']} ms")
    print(f"Latency P95:         {results['p95_ms']} ms")
    print(f"Latency P99:         {results['p99_ms']} ms")
    print(f"Errors encountered:  {len(errors)}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Opportunity Assistant Load Tester")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base API URL")
    parser.add_argument("--endpoint", default="/health", help="Target API endpoint")
    parser.add_argument("-c", "--concurrency", type=int, default=20, help="Concurrent workers")
    parser.add_argument(
        "-d", "--duration", type=float, default=10.0, help="Test duration in seconds"
    )
    args = parser.parse_args()

    asyncio.run(
        run_load_test(
            base_url=args.url,
            endpoint=args.endpoint,
            concurrency=args.concurrency,
            duration_secs=args.duration,
        )
    )


if __name__ == "__main__":
    main()
