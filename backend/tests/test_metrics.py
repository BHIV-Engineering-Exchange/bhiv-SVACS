"""Tests for app/core/metrics.py and for the monitoring endpoints in main.py.

The middleware tests need fastapi and httpx and are skipped without them.
"""

import ast
import logging
import sys
import threading
import time
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core import metrics as m
from app.core.metrics import Metrics, StageLogHandler, percentile


class Clock:
    def __init__(self, now=1_000_000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def reg(clock):
    return Metrics(clock=clock)


class TestPercentile:
    def test_empty_list_is_zero(self):
        assert percentile([], 50) == 0.0

    def test_single_value(self):
        assert percentile([7], 95) == 7.0

    def test_nearest_rank(self):
        values = list(range(1, 11))
        assert percentile(values, 50) == 5.0
        assert percentile(values, 95) == 10.0
        assert percentile(values, 100) == 10.0

    def test_order_of_input_does_not_matter(self):
        assert percentile([9, 1, 5, 3, 7], 50) == 5.0


class TestHealthSnapshot:
    def test_uptime_counts_from_creation(self, reg, clock):
        clock.advance(125)
        assert reg.health_snapshot()["uptime_seconds"] == 125

    def test_error_count_covers_only_server_errors_in_the_last_minute(self, reg, clock):
        reg.record_request("/a", "POST", 500, 10)      # will be 61 s old
        clock.advance(61)
        reg.record_request("/a", "POST", 500, 10)
        reg.record_request("/a", "GET", 503, 10)
        reg.record_request("/a", "GET", 404, 10)       # client error: not counted
        reg.record_request("/a", "GET", 200, 10)
        assert reg.health_snapshot()["error_count_60s"] == 2

    def test_ingestion_rate_counts_only_successful_posts(self, reg):
        for _ in range(3):
            reg.record_request("/up", "POST", 200, 10)
        reg.record_request("/up", "POST", 401, 1)      # rejected: not ingested
        reg.record_request("/signals", "GET", 200, 1)  # polling: not ingestion
        assert reg.health_snapshot()["ingestion_rate"] == pytest.approx(3 / 60.0, abs=1e-4)

    def test_latency_is_the_median_of_successful_posts(self, reg):
        for ms in (100, 200, 300):
            reg.record_request("/up", "POST", 200, ms)
        reg.record_request("/up", "POST", 401, 1)
        reg.record_request("/signals", "GET", 200, 1)
        snap = reg.health_snapshot()
        assert snap["processing_latency_ms"] == 200.0
        assert snap["latency_samples"] == 3

    def test_no_samples_reports_zero_with_a_zero_sample_count(self, reg):
        snap = reg.health_snapshot()
        assert snap["processing_latency_ms"] == 0.0
        assert snap["latency_samples"] == 0

    def test_old_requests_leave_the_windows(self, reg, clock):
        reg.record_request("/up", "POST", 200, 100)
        clock.advance(301)
        snap = reg.health_snapshot()
        assert snap["latency_samples"] == 0
        assert snap["ingestion_rate"] == 0.0

    def test_status_turns_degraded_at_three_errors(self, reg):
        reg.record_request("/a", "GET", 500, 1)
        reg.record_request("/a", "GET", 500, 1)
        assert reg.health_snapshot()["status"] == "ONLINE"
        reg.record_request("/a", "GET", 500, 1)
        assert reg.health_snapshot()["status"] == "DEGRADED"


# The vision_orchestrator lines from a real run (backend log, 2026-10-06
# 18:54:56). "\u2014" is the em dash the real log contains.
REAL_RUN = [
    "2026-10-06T18:54:56 | INFO     | app.services.vision_orchestrator | process_bytes() called \u2014 received 107570 bytes",
    "2026-10-06T18:54:56 | INFO     | app.services.vision_orchestrator | Image decoded OK \u2014 shape: (626, 960, 3)",
    "2026-10-06T18:54:56 | INFO     | app.services.vision_orchestrator | process_image() start \u2014 shape=(626, 960, 3) dtype=uint8 replay_id=5627ca1e-ddda-4d57-9709-358ab7a05547",
    "2026-10-06T18:54:56 | INFO     | app.services.vision_orchestrator | Stage 1 (preprocessing) OK \u2014 output shape: (626, 960, 3)",
    "2026-10-06T18:55:01 | INFO     | app.services.vision_orchestrator | Stage 2 (OCR) OK \u2014 3 results",
    "2026-10-06T18:55:02 | INFO     | app.services.vision_orchestrator | Stage 3 (detection) OK \u2014 2 detection(s)",
    "2026-10-06T18:55:02 | INFO     | app.services.vision_orchestrator | Stage 4 (explainability) OK \u2014 base64 length: 238008",
    "2026-10-06T18:55:02 | INFO     | app.services.vision_orchestrator | Stage 6 (replay save) OK \u2014 replay_id=5627ca1e-ddda-4d57-9709-358ab7a05547",
    "2026-10-06T18:55:07 | INFO     | app.services.vision_orchestrator | Stage 7 (bucket write) OK \u2014 artifact_id=c1106b3a-c6a4-4990-a75b-645ce3f4ef5c",
    "2026-10-06T18:55:07 | INFO     | app.services.vision_orchestrator | process_image() completed successfully \u2014 replay_id=5627ca1e-ddda-4d57-9709-358ab7a05547",
]


def record_from_line(line):
    stamp, level, name, message = [part.strip() for part in line.split(" | ", 3)]
    created = datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc).timestamp()
    record = logging.LogRecord(name, getattr(logging, level), "", 0, message, None, None)
    record.created = created
    return record


def replay(handler, lines):
    for line in lines:
        handler.emit(record_from_line(line))


def stage_durations(reg):
    return {e[1]: (e[2], e[3]) for e in reg._stage_events}


class TestStageLogHandler:
    def test_real_run_gives_the_expected_stage_durations(self, reg):
        replay(StageLogHandler(reg), REAL_RUN)
        assert stage_durations(reg) == {
            "preprocessing": (0.0, True),
            "ocr": (5000.0, True),
            "detection": (1000.0, True),
            "explainability": (0.0, True),
            "replay": (0.0, True),
            "bucket": (5000.0, True),
        }

    def test_failed_stage_is_recorded_as_a_failure(self, reg):
        lines = REAL_RUN[:2] + [
            "2026-10-06T18:54:56 | INFO     | app.services.vision_orchestrator | process_image() start \u2014 shape=(1, 1, 3)",
            "2026-10-06T18:54:57 | INFO     | app.services.vision_orchestrator | Stage 6 (replay save) OK \u2014 replay_id=x",
            "2026-10-06T18:55:02 | WARNING  | app.services.vision_orchestrator | Stage 7 (bucket write) FAILED (non-fatal): HTTP 503",
        ]
        replay(StageLogHandler(reg), lines)
        assert stage_durations(reg)["bucket"] == (5000.0, False)

    def test_stage_line_without_a_start_line_is_ignored(self, reg):
        replay(StageLogHandler(reg), [REAL_RUN[4]])
        assert reg._stage_events == type(reg._stage_events)()

    def test_unrelated_lines_are_ignored(self, reg):
        handler = StageLogHandler(reg)
        replay(handler, [REAL_RUN[0], REAL_RUN[1], REAL_RUN[-1]])
        assert len(reg._stage_events) == 0

    def test_a_message_with_formatting_arguments_does_not_raise(self, reg):
        record = logging.LogRecord(
            "app.services.vision_orchestrator", logging.INFO, "", 0,
            "Stage %d (%s) OK", (3, "detection"), None,
        )
        StageLogHandler(reg).emit(record)  # must not raise

    def test_each_thread_keeps_its_own_start_time(self, reg):
        handler = StageLogHandler(reg)
        start = record_from_line(REAL_RUN[2])
        other_start = record_from_line(REAL_RUN[2])
        other_start.created = start.created + 100

        handler.emit(start)
        worker = threading.Thread(target=handler.emit, args=(other_start,))
        worker.start()
        worker.join()

        stage = record_from_line(REAL_RUN[3])
        stage.created = start.created + 2
        handler.emit(stage)
        assert stage_durations(reg)["preprocessing"][0] == 2000.0

    def test_install_attaches_one_handler_however_often_it_is_called(self):
        name = "test.stage.logger.%s" % time.time()
        m.install_stage_logging(Metrics(), logger_name=name)
        m.install_stage_logging(Metrics(), logger_name=name)
        handlers = [h for h in logging.getLogger(name).handlers if isinstance(h, StageLogHandler)]
        assert len(handlers) == 1


ALLOWED_STATUS = {"live", "degraded", "stale", "down"}
STAGE_FIELDS = {"stage", "events_per_sec", "total_events", "p50_latency_ms",
                "p95_latency_ms", "error_rate", "status"}


class TestStageMetrics:
    def test_all_pipeline_stages_are_listed_from_the_start_as_stale(self, reg):
        result = reg.stage_metrics()
        assert [s["stage"] for s in result] == m.STAGE_ORDER
        assert all(s["status"] == "stale" and s["total_events"] == 0 for s in result)

    def test_entries_carry_exactly_the_fields_the_dashboard_expects(self, reg):
        reg.record_stage("ocr", 120, True)
        for entry in reg.stage_metrics():
            assert set(entry) == STAGE_FIELDS
            assert entry["status"] in ALLOWED_STATUS

    def test_live_stage_reports_latency_percentiles(self, reg):
        for ms in (100, 200, 300, 400):
            reg.record_stage("ocr", ms, True)
        ocr = [s for s in reg.stage_metrics() if s["stage"] == "ocr"][0]
        assert ocr["status"] == "live"
        assert ocr["total_events"] == 4
        assert ocr["p50_latency_ms"] == 200.0
        assert ocr["p95_latency_ms"] == 400.0
        assert ocr["error_rate"] == 0.0

    def test_some_failures_make_a_stage_degraded_and_many_make_it_down(self, reg):
        for ok in (True, True, True, False):
            reg.record_stage("bucket", 50, ok)
        for ok in (True, False, False):
            reg.record_stage("replay", 50, ok)
        stages = {s["stage"]: s for s in reg.stage_metrics()}
        assert stages["bucket"]["status"] == "degraded"
        assert stages["bucket"]["error_rate"] == 0.25
        assert stages["replay"]["status"] == "down"

    def test_a_stage_goes_stale_after_the_window_but_keeps_its_lifetime_total(self, reg, clock):
        reg.record_stage("detection", 80, True)
        clock.advance(301)
        detection = [s for s in reg.stage_metrics() if s["stage"] == "detection"][0]
        assert detection["status"] == "stale"
        assert detection["total_events"] == 1


class TestBucketStatus:
    def test_nothing_attempted_yet(self, reg):
        assert reg.bucket_status() == {
            "sync_percent": 0.0,
            "stages_synced": [],
            "last_sync_utc": "",
            "pending_writes": 0,
            "failed_writes": 0,
        }

    def test_mixed_outcomes(self, reg):
        for ok in (True, True, True, False):
            reg.record_stage("bucket", 10, ok)
        status = reg.bucket_status()
        assert status["sync_percent"] == 0.75
        assert status["failed_writes"] == 1
        assert status["stages_synced"] == ["perception"]
        assert datetime.fromisoformat(status["last_sync_utc"])

    def test_only_failures_means_nothing_synced(self, reg):
        reg.record_stage("bucket", 10, False)
        reg.record_stage("bucket", 10, False)
        status = reg.bucket_status()
        assert status["sync_percent"] == 0.0
        assert status["stages_synced"] == []
        assert status["last_sync_utc"] == ""
        assert status["failed_writes"] == 2

    def test_other_stages_do_not_affect_bucket_numbers(self, reg):
        reg.record_stage("ocr", 10, False)
        assert reg.bucket_status()["failed_writes"] == 0


class TestValidationBreakdown:
    def test_statuses_map_to_allow_flag_deny(self, reg):
        for status in ("OK", "OK", "FLAG", "DENY", "ok"):
            reg.record_validation(status)
        assert reg.validation_breakdown() == {"allow": 3, "flag": 1, "deny": 1, "total": 5}

    def test_unknown_status_is_ignored(self, reg):
        reg.record_validation("WATCH")
        reg.record_validation(None)
        assert reg.validation_breakdown()["total"] == 0


class TestSummary:
    def test_routes_are_aggregated_and_the_minute_series_is_complete(self, reg):
        reg.record_request("/up", "POST", 200, 100)
        reg.record_request("/up", "POST", 500, 300)
        reg.record_request("/signals", "GET", 200, 2)
        summary = reg.summary()
        by_route = {(r["route"], r["method"]): r for r in summary["by_route"]}
        assert by_route[("/up", "POST")]["count"] == 2
        assert by_route[("/up", "POST")]["errors_5xx"] == 1
        assert by_route[("/up", "POST")]["max_ms"] == 300.0
        assert by_route[("/signals", "GET")]["count"] == 1
        series = summary["requests_per_minute_last_hour"]
        assert len(series) == 60
        assert sum(p["count"] for p in series) == 3
        assert {"stages", "bucket", "validation", "health"} <= set(summary)


@pytest.fixture
def web():
    pytest.importorskip("httpx")
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    registry = Metrics()
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware, allow_origins=["http://localhost:5173"],
        allow_methods=["*"], allow_headers=["*"],
    )
    app.add_middleware(m.MetricsMiddleware, registry=registry)

    @app.get("/items/{item_id}")
    def item(item_id: int):
        return {"id": item_id}

    @app.post("/slow")
    def slow():
        time.sleep(0.05)
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("unhandled")

    @app.get("/teapot")
    def teapot():
        raise HTTPException(status_code=418, detail="short and stout")

    return TestClient(app, raise_server_exceptions=False), registry


def recorded(registry):
    return [(r[1], r[2], r[3]) for r in registry._requests]


class TestMiddleware:
    def test_path_parameters_are_grouped_under_the_route_template(self, web):
        client, registry = web
        client.get("/items/1")
        client.get("/items/2")
        assert recorded(registry) == [("/items/{item_id}", "GET", 200)] * 2

    def test_unknown_paths_share_one_bucket(self, web):
        client, registry = web
        client.get("/nope/1")
        client.get("/nope/2")
        assert recorded(registry) == [("<unmatched>", "GET", 404)] * 2

    def test_cors_preflights_are_labelled_separately(self, web):
        client, registry = web
        client.options("/slow", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        })
        assert recorded(registry) == [("<preflight>", "OPTIONS", 200)]

    def test_unhandled_exception_is_recorded_as_a_server_error(self, web):
        client, registry = web
        assert client.get("/boom").status_code == 500
        assert recorded(registry) == [("/boom", "GET", 500)]
        assert registry.health_snapshot()["error_count_60s"] == 1

    def test_handled_http_errors_keep_their_status(self, web):
        client, registry = web
        assert client.get("/teapot").status_code == 418
        assert recorded(registry) == [("/teapot", "GET", 418)]

    def test_duration_is_measured(self, web):
        client, registry = web
        client.post("/slow")
        assert registry._requests[0][4] >= 40.0

    def test_responses_and_cors_headers_are_not_altered(self, web):
        client, _ = web
        response = client.get("/items/7", headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 200
        assert response.json() == {"id": 7}
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


MAIN_PY = Path(m.__file__).resolve().parents[1] / "main.py"
MAIN_SOURCE = MAIN_PY.read_text(encoding="utf-8-sig")
MAIN_TREE = ast.parse(MAIN_SOURCE)


def handler_source(name):
    for node in ast.walk(MAIN_TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(MAIN_SOURCE, node)
    raise AssertionError("function %s not found in main.py" % name)


def load_handler(name, registry, monkeypatch):
    """Run the real handler source from main.py against a given registry,
    with the model modules stubbed out."""
    inference = types.SimpleNamespace(yolo_model=None, classifier_model=object())
    ocr = types.SimpleNamespace(reader=None)
    monkeypatch.setitem(sys.modules, "app.services.inference_service",
                        types.SimpleNamespace(inference_service=inference))
    monkeypatch.setitem(sys.modules, "app.services.ocr_service",
                        types.SimpleNamespace(ocr_service=ocr))

    class FakeApp:
        def get(self, *a, **k):
            return lambda f: f

    namespace = {
        "app": FakeApp(),
        "metrics": registry,
        "settings": types.SimpleNamespace(PROJECT_NAME="test-service"),
        "datetime": datetime,
        "timezone": timezone,
    }
    source = handler_source(name)
    exec(compile(source, "main.py:%s" % name, "exec"), namespace)
    return namespace[name]


class TestMainPyUsesLiveMetrics:
    FAKE_LITERALS = [
        '"events_per_sec": 18.4',
        '"uptime_seconds": 3600',
        '"total_events": 60',
        '"sync_percent": 1.0',
        '"allow": 80',
        '"processing_latency_ms": 12.0',
    ]

    @pytest.mark.parametrize("literal", FAKE_LITERALS)
    def test_old_hardcoded_numbers_are_gone(self, literal):
        assert literal not in MAIN_SOURCE

    @pytest.mark.parametrize(
        "name",
        ["health", "get_stage_metrics", "get_bucket_status",
         "get_validation_breakdown", "get_metrics"],
    )
    def test_monitoring_handlers_read_from_the_registry(self, name):
        assert "metrics." in handler_source(name)

    def test_middleware_and_stage_logging_are_installed(self):
        assert "app.add_middleware(MetricsMiddleware)" in MAIN_SOURCE
        assert "install_stage_logging()" in MAIN_SOURCE

    def test_every_analysed_image_is_counted_in_the_validation_breakdown(self):
        assert 'metrics.record_validation(result["validation_status"])' in handler_source("upload_image")

    def test_health_matches_the_fields_the_dashboard_reads(self, reg, monkeypatch):
        reg.record_request("/intelligence/image", "POST", 200, 250)
        frame = load_handler("health", reg, monkeypatch)()
        for field in ("ingestion_rate", "processing_latency_ms",
                      "error_count_60s", "uptime_seconds"):
            assert isinstance(frame[field], (int, float)), field
        assert isinstance(frame["last_telemetry_utc"], str)
        assert frame["ws_connected"] is False   # this backend serves no websocket
        assert frame["processing_latency_ms"] == 250.0

    def test_stage_metrics_endpoint_returns_dashboard_shaped_entries(self, reg, monkeypatch):
        reg.record_stage("bucket", 40, True)
        entries = load_handler("get_stage_metrics", reg, monkeypatch)()
        assert entries and all(set(e) == STAGE_FIELDS for e in entries)
        assert all(e["status"] in ALLOWED_STATUS for e in entries)

    def test_bucket_status_endpoint_matches_the_dashboard_fields(self, reg, monkeypatch):
        status = load_handler("get_bucket_status", reg, monkeypatch)()
        assert set(status) == {"sync_percent", "stages_synced", "last_sync_utc",
                               "pending_writes", "failed_writes"}
        assert isinstance(status["last_sync_utc"], str)

    def test_validation_breakdown_endpoint_has_the_four_counts(self, reg, monkeypatch):
        reg.record_validation("OK")
        counts = load_handler("get_validation_breakdown", reg, monkeypatch)()
        assert counts == {"allow": 1, "flag": 0, "deny": 0, "total": 1}
