"""Source registry: maps a name to a configured :class:`DemandSource`.

This is the one place that knows how to *construct* each source. The API and
service layers only ask the registry for a source by name, so wiring a new feed
in is a single ``register`` call here.
"""

from __future__ import annotations

from energy_tracker.config import Settings
from energy_tracker.sources.base import DemandSource, SourceError
from energy_tracker.sources.eia930 import EIA930Source
from energy_tracker.sources.fixture import FixtureSource


class SourceRegistry:
    """Lazily builds and caches source instances from settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._instances: dict[str, DemandSource] = {}
        # Factories, not instances, so we only construct what's actually used
        # (e.g. no httpx client created unless EIA is requested).
        self._factories = {
            FixtureSource.name: self._make_fixture,
            EIA930Source.name: self._make_eia930,
        }

    def names(self) -> list[str]:
        return sorted(self._factories)

    def get(self, name: str) -> DemandSource:
        if name not in self._factories:
            raise SourceError(
                f"unknown source '{name}'; available: {', '.join(self.names())}"
            )
        if name not in self._instances:
            self._instances[name] = self._factories[name]()
        return self._instances[name]

    # -- factories ---------------------------------------------------------

    def _make_fixture(self) -> DemandSource:
        return FixtureSource()

    def _make_eia930(self) -> DemandSource:
        return EIA930Source(
            api_key=self._settings.eia_api_key,
            timeout=self._settings.http_timeout_seconds,
        )
