"""Live runtime metrics for the SVACS backend (standard library only).

Everything reported by /health, /stage-metrics, /bucket/status,
/validation-breakdown and /metrics is computed from real traffic recorded
here. Nothing is a placeholder.

What is recorded
----------------
* Every HTTP request: route template, method, status code, duration
  (MetricsMiddleware).
* Every image-pipeline stage: duration and outcome, measured from the
  "Stage N (name) OK/FAILED" log lines that vision_orchestrator already
  writes (StageLogHandler). The time for a stage is the gap since the
  previous stage line of the same request. This needs no change to
  vision_orchestrator.py, but it does depend on that log wording; the
  tests in tests/test_metrics.py use the real log lines to guard it.
* Validation outcomes (OK / FLAG / DENY) of analysed images.

Limits
------
* Held in memory per process: restarting the server resets everything,
  and several worker processes would each keep their own numbers.
* Only the most recent MAX_EVENTS requests and stage events are kept, so
  percentiles describe recent traffic, not all time. Stage and Bucket
  totals (lifetime since start) are exact.
"""

import logging
import math
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

MAX_EVENTS = 5000
DEGRADED_ERROR_THRESHOLD = 3

# Pipeline order, and the short names used in the dashboard. The name in
# the log line (inside the brackets) is mapped to the name reported here.
STAGE_ORDER = ["preprocessing", "ocr", "detection", "explainability", "replay", "bucket"]
STAGE_NAMES = {
    "preprocessing": "preprocessing",
    "ocr": "ocr",
    "detection": "detection",
    "explainability": "explainability",
    "replay save": "replay",
    "bucket write": "bucket",
}

_START_LINE = re.compile(r"^process_image\(\) start")
_STAGE_LINE = re.compile(r"^Stage (\d+) \(([^)]+)\) (OK|FAILED)")

_VALIDATION_BUCKETS = {"OK": "allow", "ALLOW": "allow", "FLAG": "flag", "DENY": "deny"}


def percentile(values, pct):
    """Nearest-rank percentile. Returns 0.0 for an empty list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return float(ordered[min(rank, len(ordered)) - 1])


def _iso(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


class Metrics:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._started = clock()
        self._lock = threading.Lock()
        # (timestamp, route, method, status, duration_ms)
        self._requests = deque(maxlen=MAX_EVENTS)
        # (timestamp, stage, duration_ms, ok)
        self._stage_events = deque(maxlen=MAX_EVENTS)
        self._stage_lifetime = defaultdict(lambda: {"ok": 0, "failed": 0, "last_ok": None})
        self._validation = {"allow": 0, "flag": 0, "deny": 0}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record_request(self, route, method, status, duration_ms):
        with self._lock:
            self._requests.append((self._clock(), route, method, int(status), float(duration_ms)))

    def record_stage(self, stage, duration_ms, ok):
        now = self._clock()
        with self._lock:
            self._stage_events.append((now, stage, float(duration_ms), bool(ok)))
            life = self._stage_lifetime[stage]
            if ok:
                life["ok"] += 1
                life["last_ok"] = now
            else:
                life["failed"] += 1

    def record_validation(self, status):
        bucket = _VALIDATION_BUCKETS.get(str(status).upper())
        if bucket is None:
            return
        with self._lock:
            self._validation[bucket] += 1

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    def health_snapshot(self, rate_window=60, latency_window=300):
        """Numbers for /health.

        ingestion_rate is successful POST requests per second over the last
        rate_window seconds. processing_latency_ms is the median duration of
        successful POST requests over the last latency_window seconds
        (0.0 with latency_samples == 0 when there are none).
        """
        now = self._clock()
        with self._lock:
            requests = list(self._requests)
        recent = [r for r in requests if now - r[0] <= rate_window]
        ok_posts_recent = [r for r in recent if r[2] == "POST" and 200 <= r[3] < 300]
        errors = sum(1 for r in recent if 500 <= r[3] < 600)
        latencies = [
            r[4]
            for r in requests
            if r[2] == "POST" and 200 <= r[3] < 300 and now - r[0] <= latency_window
        ]
        return {
            "status": "DEGRADED" if errors >= DEGRADED_ERROR_THRESHOLD else "ONLINE",
            "ingestion_rate": round(len(ok_posts_recent) / float(rate_window), 4),
            "processing_latency_ms": round(percentile(latencies, 50), 1),
            "latency_samples": len(latencies),
            "error_count_60s": errors,
            "uptime_seconds": int(now - self._started),
        }

    def stage_metrics(self, window=300):
        """One entry per image-pipeline stage, in pipeline order.

        status is one of the four values the dashboard understands:
        live (recent events, no failures), degraded (some failures),
        down (half or more failed) or stale (no events in the window).
        """
        now = self._clock()
        with self._lock:
            events = list(self._stage_events)
            lifetime = {k: dict(v) for k, v in self._stage_lifetime.items()}
        names = list(STAGE_ORDER) + sorted(n for n in lifetime if n not in STAGE_ORDER)
        result = []
        for name in names:
            recent = [e for e in events if e[1] == name and now - e[0] <= window]
            life = lifetime.get(name, {"ok": 0, "failed": 0})
            failed = sum(1 for e in recent if not e[3])
            durations = [e[2] for e in recent]
            error_rate = (failed / len(recent)) if recent else 0.0
            if not recent:
                status = "stale"
            elif error_rate >= 0.5:
                status = "down"
            elif error_rate > 0:
                status = "degraded"
            else:
                status = "live"
            result.append(
                {
                    "stage": name,
                    "events_per_sec": round(len(recent) / float(window), 4),
                    "total_events": life["ok"] + life["failed"],
                    "p50_latency_ms": round(percentile(durations, 50), 1),
                    "p95_latency_ms": round(percentile(durations, 95), 1),
                    "error_rate": round(error_rate, 4),
                    "status": status,
                }
            )
        return result

    def bucket_status(self):
        """Bucket write outcomes since the server started.

        Writes are made inline during the request, so nothing is ever queued
        (pending_writes is 0). The only artifact this backend writes is the
        vision detection result, which is the output of the perception
        stage, so that is the stage reported as synced.
        """
        with self._lock:
            life = dict(self._stage_lifetime.get("bucket", {"ok": 0, "failed": 0, "last_ok": None}))
        attempts = life["ok"] + life["failed"]
        return {
            "sync_percent": round(life["ok"] / float(attempts), 4) if attempts else 0.0,
            "stages_synced": ["perception"] if life["ok"] else [],
            "last_sync_utc": _iso(life["last_ok"]) if life["last_ok"] else "",
            "pending_writes": 0,
            "failed_writes": life["failed"],
        }

    def validation_breakdown(self):
        with self._lock:
            counts = dict(self._validation)
        counts["total"] = counts["allow"] + counts["flag"] + counts["deny"]
        return counts

    def summary(self):
        """Everything, for the /metrics endpoint."""
        now = self._clock()
        with self._lock:
            requests = list(self._requests)

        by_route = defaultdict(list)
        for ts, route, method, status, ms in requests:
            by_route[(route, method)].append((status, ms))
        routes = []
        for (route, method), items in sorted(by_route.items()):
            durations = [ms for _, ms in items]
            routes.append(
                {
                    "route": route,
                    "method": method,
                    "count": len(items),
                    "errors_5xx": sum(1 for s, _ in items if 500 <= s < 600),
                    "p50_ms": round(percentile(durations, 50), 1),
                    "p95_ms": round(percentile(durations, 95), 1),
                    "max_ms": round(max(durations), 1),
                }
            )

        minutes = {}
        for ts, _route, _method, status, _ms in requests:
            if now - ts > 3600:
                continue
            key = int(ts // 60) * 60
            entry = minutes.setdefault(key, {"count": 0, "errors": 0})
            entry["count"] += 1
            if 500 <= status < 600:
                entry["errors"] += 1
        current = int(now // 60) * 60
        series = [
            {
                "minute_utc": _iso(minute),
                "count": minutes.get(minute, {"count": 0})["count"],
                "errors": minutes.get(minute, {"errors": 0})["errors"],
            }
            for minute in range(current - 59 * 60, current + 60, 60)
        ]

        return {
            "uptime_seconds": int(now - self._started),
            "started_utc": _iso(self._started),
            "requests_retained": len(requests),
            "requests_retention_limit": MAX_EVENTS,
            "by_route": routes,
            "requests_per_minute_last_hour": series,
            "stages": self.stage_metrics(window=3600),
            "bucket": self.bucket_status(),
            "validation": self.validation_breakdown(),
            "health": self.health_snapshot(),
        }


metrics = Metrics()


class StageLogHandler(logging.Handler):
    """Turns vision_orchestrator's stage log lines into stage timings."""

    def __init__(self, registry):
        super().__init__(level=logging.INFO)
        self._registry = registry
        self._local = threading.local()

    def emit(self, record):
        try:
            message = record.getMessage()
            if _START_LINE.match(message):
                self._local.mark = record.created
                return
            match = _STAGE_LINE.match(message)
            if not match:
                return
            mark = getattr(self._local, "mark", None)
            if mark is None:
                return
            duration_ms = max(0.0, (record.created - mark) * 1000.0)
            self._local.mark = record.created
            raw_name = match.group(2).strip().lower()
            self._registry.record_stage(
                STAGE_NAMES.get(raw_name, raw_name), duration_ms, match.group(3) == "OK"
            )
        except Exception:  # a logging handler must never break the request
            self.handleError(record)


def install_stage_logging(registry=None, logger_name="app.services.vision_orchestrator"):
    """Attach the stage timing handler once (safe to call repeatedly)."""
    target = logging.getLogger(logger_name)
    if not any(isinstance(h, StageLogHandler) for h in target.handlers):
        target.addHandler(StageLogHandler(registry or metrics))


class MetricsMiddleware:
    """Records every HTTP request. Pure ASGI, so it cannot change responses."""

    def __init__(self, app, registry=None):
        self.app = app
        self.registry = registry or metrics

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status = {"code": 0}  # 0 means no response was sent (client went away)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            if status["code"] == 0:
                status["code"] = 500
            raise
        finally:
            route = getattr(scope.get("route"), "path", None)
            if route is None:
                route = "<preflight>" if scope.get("method") == "OPTIONS" else "<unmatched>"
            self.registry.record_request(
                route,
                scope.get("method", ""),
                status["code"],
                (time.perf_counter() - started) * 1000.0,
            )
