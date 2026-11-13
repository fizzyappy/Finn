"""Offline test setup: a fresh temporary database per test, no network access."""
from __future__ import annotations

from pathlib import Path

import pytest

from finn import http, store, symbols

FIX = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def fixture_bytes(name: str) -> bytes:
    return (FIX / name).read_bytes()


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    s = store.Store(tmp_path / "test.sqlite")
    store.use_store(s)
    monkeypatch.setattr("finn.config.DOCS_DIR", tmp_path / "docs")
    http.reset_blocks()

    def no_network(*a, **k):
        raise AssertionError("tests must not touch the network")

    monkeypatch.setattr(http, "get", no_network)
    master = symbols.parse_master(fixture_text("EQUITY_L_sample.csv"))
    monkeypatch.setattr(symbols, "nse_master", lambda refresh=False: master)
    yield s
    s.conn.close()
