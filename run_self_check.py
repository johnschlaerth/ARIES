"""Run ARIES non-GUI readiness checks."""

from __future__ import annotations

import argparse

from aries.self_check import run_self_check


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ARIES non-GUI readiness checks.")
    parser.add_argument("--write-reports", action="store_true", help="Also write mission report outputs.")
    args = parser.parse_args()
    ok, messages = run_self_check(write_outputs=args.write_reports)
    for message in messages:
        print(message)
    if ok:
        print("ARIES self-check passed")
        raise SystemExit(0)
    print("ARIES self-check failed")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
