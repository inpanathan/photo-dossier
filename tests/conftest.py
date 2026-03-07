"""Shared test fixtures and environment isolation.

Overrides environment variables to ensure tests run deterministically
against mocks, not real services (REQ-TST-051).
"""

from __future__ import annotations

import os

# Override env vars before any app code loads settings
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "true")
