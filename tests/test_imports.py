"""Smoke test: every entry point the scheduled tasks run must at least import.

Added 2026-10-12 after a syntax error in run_paper.py passed the whole suite
because nothing imported it.
"""
import importlib

import pytest


@pytest.mark.parametrize("mod", [
    "jcoin.live.run_paper",
    "jcoin.live.run_kraken",
    "jcoin.live.watchdog",
    "jcoin.live.daemon",
    "jcoin.live.paper_runner",
])
def test_entry_point_imports(mod):
    importlib.import_module(mod)
