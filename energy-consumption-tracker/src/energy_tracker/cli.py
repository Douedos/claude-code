"""Tiny CLI to see output without starting the server.

    python -m energy_tracker.cli --regions PJM,CISO,ERCO
    python -m energy_tracker.cli --source eia930 --regions PJM   # needs EIA_API_KEY

Prints the latest demand per region as a simple table.
"""

from __future__ import annotations

import argparse

from energy_tracker.config import load_settings
from energy_tracker.registry import SourceRegistry
from energy_tracker.service import DemandService
from energy_tracker.sources.base import SourceError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Latest US electricity demand")
    parser.add_argument("--regions", default="PJM,MISO,ERCO,CISO",
                        help="Comma-separated region codes")
    parser.add_argument("--source", default=None, help="Source name (default from config)")
    parser.add_argument("--lookback-hours", type=int, default=48)
    args = parser.parse_args(argv)

    settings = load_settings()
    service = DemandService(SourceRegistry(settings), settings.cache_ttl_seconds)
    source = args.source or settings.default_source
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]

    try:
        rows = service.get_latest(source, regions, lookback_hours=args.lookback_hours)
    except SourceError as exc:
        print(f"error: {exc}")
        return 1

    print(f"source: {source}")
    print(f"{'region':8}  {'timestamp (UTC)':20}  {'demand':>12}  unit")
    print("-" * 52)
    for o in rows:
        ts = o.timestamp.strftime("%Y-%m-%d %H:%M")
        print(f"{o.region:8}  {ts:20}  {o.value:>12,.1f}  {o.unit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
