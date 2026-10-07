"""API key authentication for the SVACS backend.

How it works
------------
The expected key is read from the SVACS_API_KEY environment variable.
Protected endpoints require the same value in the X-API-Key request header.

  * SVACS_API_KEY set     -> protected endpoints require the key
                             (401 if it is missing, 403 if it is wrong).
  * SVACS_API_KEY not set -> protected endpoints stay open and the server
                             logs a warning at startup. This keeps local
                             development working without any setup; set the
                             variable on any server reachable by others.

Scope
-----
Attach require_api_key to a route with
    @app.post("/path", dependencies=[Depends(require_api_key)])
tests/test_security.py checks that every POST route in app/main.py does so.

Limits to be aware of
---------------------
This is a shared secret, not user login. When the dashboard sends it from
the browser, anyone who can load the dashboard can read it from the page.
It stops scripts and scanners that call the API directly without the key;
it does not identify individual users.
"""

import logging
import os
import secrets
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

API_KEY_ENV_VAR = "SVACS_API_KEY"
API_KEY_HEADER_NAME = "X-API-Key"

# auto_error=False so that this module decides the status codes and messages.
_api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def configured_api_key() -> Optional[str]:
    """Return the configured key, or None when none is set.

    Read on every call (not at import time) so a restart or a test that
    changes the environment is picked up without reloading the module.
    """
    value = os.getenv(API_KEY_ENV_VAR, "").strip()
    return value or None


def auth_enabled() -> bool:
    return configured_api_key() is not None


async def require_api_key(provided: Optional[str] = Security(_api_key_header)) -> None:
    """FastAPI dependency: reject the request unless it carries the right key."""
    expected = configured_api_key()
    if expected is None:
        return  # authentication not configured; see module docstring

    if not provided:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Send it in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # compare_digest runs in constant time, and comparing bytes keeps a
    # non-ASCII header value from raising a TypeError.
    if not secrets.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        logger.warning("Rejected request with an invalid API key.")
        raise HTTPException(status_code=403, detail="Invalid API key.")
