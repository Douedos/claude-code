"""The contract every data source implements.

Adding a new feed (PJM, CAISO, EPA CEMS, a commercial API…) means writing one
class that subclasses ``DemandSource`` and returns ``DemandObservation``s. The
service and API layers stay untouched. That is the extension seam the rest of
the project is built around.
"""

from __future__ import annotations

import abc
from collections.abc import Sequence
from datetime import datetime

from energy_tracker.models import DemandObservation, Metric, SourceInfo


class SourceError(RuntimeError):
    """Raised when a source cannot satisfy a request (network, auth, bad args).

    The service layer catches this and turns it into a clean API error rather
    than leaking transport-specific exceptions to callers.
    """


class DemandSource(abc.ABC):
    """Abstract base for all demand data providers."""

    #: Stable identifier used in the registry and API (e.g. "eia930").
    name: str

    @abc.abstractmethod
    def info(self) -> SourceInfo:
        """Describe this source for discovery endpoints."""

    @abc.abstractmethod
    def fetch(
        self,
        regions: Sequence[str],
        start: datetime,
        end: datetime,
        metric: Metric = Metric.DEMAND,
    ) -> list[DemandObservation]:
        """Return observations for the given regions and half-open [start, end)
        UTC window.

        Implementations should:
          * accept timezone-aware UTC datetimes,
          * return results sorted by (region, timestamp),
          * raise :class:`SourceError` on any failure.
        """

    def health(self) -> bool:
        """Cheap liveness check. Override for real upstream pings.

        Default assumes a source with no external dependency is always healthy.
        """
        return True
