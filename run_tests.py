"""Run the ARIES deterministic testbench."""

from __future__ import annotations

try:
    import pytest
except ImportError as exc:
    raise SystemExit(
        "pytest is not installed. Create/activate a Python 3.11 or 3.12 virtual environment, "
        "then run `pip install -r requirements.txt`."
    ) from exc


if __name__ == "__main__":
    raise SystemExit(pytest.main(["tests"]))
