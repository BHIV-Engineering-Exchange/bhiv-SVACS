"""Tests for API key authentication (app/core/security.py) and its wiring.

Needs only fastapi. The wiring tests also need httpx (pip install httpx);
they are skipped if it is missing.
"""

import ast
import asyncio
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core import security

KEY = "test-key-123"
ORIGIN = "http://localhost:5173"


def call(provided):
    return asyncio.run(security.require_api_key(provided))


class TestRequireApiKey:
    def test_open_when_no_key_is_configured(self, monkeypatch):
        monkeypatch.delenv("SVACS_API_KEY", raising=False)
        assert security.auth_enabled() is False
        assert call(None) is None
        assert call("anything") is None

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_key_counts_as_not_configured(self, monkeypatch, blank):
        monkeypatch.setenv("SVACS_API_KEY", blank)
        assert security.auth_enabled() is False
        assert call(None) is None

    def test_missing_key_is_401(self, monkeypatch):
        monkeypatch.setenv("SVACS_API_KEY", KEY)
        with pytest.raises(HTTPException) as err:
            call(None)
        assert err.value.status_code == 401
        assert err.value.headers == {"WWW-Authenticate": "ApiKey"}

    def test_empty_header_is_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("SVACS_API_KEY", KEY)
        with pytest.raises(HTTPException) as err:
            call("")
        assert err.value.status_code == 401

    def test_wrong_key_is_403(self, monkeypatch):
        monkeypatch.setenv("SVACS_API_KEY", KEY)
        with pytest.raises(HTTPException) as err:
            call("not-the-key")
        assert err.value.status_code == 403

    def test_correct_key_passes(self, monkeypatch):
        monkeypatch.setenv("SVACS_API_KEY", KEY)
        assert call(KEY) is None

    def test_key_is_case_sensitive(self, monkeypatch):
        monkeypatch.setenv("SVACS_API_KEY", KEY)
        with pytest.raises(HTTPException) as err:
            call(KEY.upper())
        assert err.value.status_code == 403

    def test_non_ascii_header_value_is_rejected_cleanly(self, monkeypatch):
        monkeypatch.setenv("SVACS_API_KEY", KEY)
        with pytest.raises(HTTPException) as err:
            call("k\u00e9y")
        assert err.value.status_code == 403

    def test_whitespace_around_the_configured_key_is_trimmed(self, monkeypatch):
        monkeypatch.setenv("SVACS_API_KEY", "  " + KEY + "  ")
        assert call(KEY) is None

    def test_key_is_read_on_every_call_not_cached(self, monkeypatch):
        monkeypatch.delenv("SVACS_API_KEY", raising=False)
        assert call(None) is None
        monkeypatch.setenv("SVACS_API_KEY", KEY)
        with pytest.raises(HTTPException):
            call(None)


@pytest.fixture
def client(monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    monkeypatch.setenv("SVACS_API_KEY", KEY)
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGIN],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/protected", dependencies=[Depends(security.require_api_key)])
    def protected():
        return {"ok": True}

    @app.get("/open")
    def open_route():
        return {"ok": True}

    return TestClient(app)


class TestWiringBehindCors:
    def test_protected_route_rejects_a_request_without_the_key(self, client):
        assert client.post("/protected").status_code == 401

    def test_protected_route_rejects_a_wrong_key(self, client):
        assert client.post("/protected", headers={"X-API-Key": "nope"}).status_code == 403

    def test_protected_route_accepts_the_right_key(self, client):
        response = client.post("/protected", headers={"X-API-Key": KEY})
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_open_route_needs_no_key(self, client):
        assert client.get("/open").status_code == 200

    def test_auth_errors_still_carry_cors_headers(self, client):
        """Without these the browser shows an unreadable 'Failed to fetch'
        instead of the 401, which hides the real cause from the user."""
        response = client.post("/protected", headers={"Origin": ORIGIN})
        assert response.status_code == 401
        assert response.headers.get("access-control-allow-origin") == ORIGIN

    def test_preflight_for_the_key_header_is_allowed(self, client):
        """Browsers send an OPTIONS preflight before a request with a custom
        header. It must succeed without the key itself."""
        response = client.options(
            "/protected",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-api-key",
            },
        )
        assert response.status_code == 200
        assert "x-api-key" in response.headers.get("access-control-allow-headers", "").lower()


MAIN_PY = Path(security.__file__).resolve().parents[1] / "main.py"


def _post_routes():
    """Return (function_name, is_protected) for every @app.post route in
    main.py, read from the source text so the heavy model imports are not
    needed."""
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8-sig"))
    routes = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "post"
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "app"
            ):
                protected = any(
                    kw.arg == "dependencies" and "require_api_key" in ast.dump(kw.value)
                    for kw in decorator.keywords
                )
                routes.append((node.name, protected))
    return routes


class TestMainPyPolicy:
    def test_main_py_has_post_routes_to_check(self):
        assert _post_routes(), "no @app.post routes found; has main.py moved?"

    def test_every_post_endpoint_requires_the_api_key(self):
        """Every POST route runs a model or accepts data. A new one added
        without dependencies=[Depends(require_api_key)] fails here."""
        unprotected = [name for name, protected in _post_routes() if not protected]
        assert not unprotected, "POST routes without the API key check: %s" % unprotected
