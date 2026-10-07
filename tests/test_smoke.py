"""Smoke test: the package imports and exposes a version."""

import lead_agent


def test_package_exposes_version() -> None:
    assert lead_agent.__version__ == "0.1.0"
