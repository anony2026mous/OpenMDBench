"""Unit tests for the in-memory session limiter."""

import pytest
from openmdbench.api.sessions import SessionStore


def test_session_rate_limit_is_scoped_per_session() -> None:
    store = SessionStore(rate_limit=1, rate_window_seconds=60.0)
    first = store.create("MD-REC-001", 1)
    second = store.create("MD-REC-001", 2)
    store.check_rate_limit(first)
    with pytest.raises(RuntimeError, match="rate limit"):
        store.check_rate_limit(first)
    store.check_rate_limit(second)
