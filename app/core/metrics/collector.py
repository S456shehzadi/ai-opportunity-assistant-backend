"""Application metrics collector for Prometheus and observability dashboards."""

from __future__ import annotations

import threading
import time
from typing import Any


class MetricsCollector:
    """Thread-safe collector for high-cardinality application and infrastructure metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {
            "http_requests_total": 0,
            "http_errors_total": 0,
            "search_queries_total": 0,
            "search_provider_failures_total": 0,
            "ai_inferences_total": 0,
            "ai_fallback_total": 0,
            "worker_jobs_total": 0,
            "worker_job_failures_total": 0,
            "notifications_generated_total": 0,
            "notifications_delivered_total": 0,
            "notifications_failed_total": 0,
        }
        self._latencies: dict[str, list[float]] = {
            "http_request_duration_ms": [],
            "search_duration_ms": [],
            "ai_duration_ms": [],
        }

    def increment(self, name: str, amount: int = 1) -> None:
        """Increments a monotonic counter."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def record_latency(self, name: str, duration_ms: float) -> None:
        """Appends an execution latency observation."""
        with self._lock:
            buf = self._latencies.setdefault(name, [])
            buf.append(duration_ms)
            if len(buf) > 1000:
                del buf[:500]

    def get_snapshot(self) -> dict[str, Any]:
        """Returns structured JSON metrics representation."""
        with self._lock:
            latencies_summary = {}
            for k, v in self._latencies.items():
                if v:
                    latencies_summary[k] = {
                        "count": len(v),
                        "avg": round(sum(v) / len(v), 2),
                        "max": round(max(v), 2),
                        "min": round(min(v), 2),
                    }
                else:
                    latencies_summary[k] = {"count": 0, "avg": 0.0, "max": 0.0, "min": 0.0}

            return {
                "counters": dict(self._counters),
                "latencies": latencies_summary,
                "timestamp": int(time.time()),
            }

    def format_prometheus(self) -> str:
        """Generates Prometheus text-formatted exposition metric payload."""
        lines = []
        with self._lock:
            for name, val in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {val}")

            for name, vals in self._latencies.items():
                if vals:
                    avg_val = sum(vals) / len(vals)
                    lines.append(f"# TYPE {name} gauge")
                    lines.append(f"{name} {avg_val:.2f}")

        return "\n".join(lines) + "\n"

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, latency_ms: float
    ) -> None:
        """Records an HTTP request and latency."""
        self.increment("http_requests_total")
        if status_code >= 400:
            self.increment("http_errors_total")
        self.record_latency("http_request_duration_ms", latency_ms)


_default_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    global _default_metrics_collector
    if _default_metrics_collector is None:
        _default_metrics_collector = MetricsCollector()
    return _default_metrics_collector


metrics_collector = get_metrics_collector()
