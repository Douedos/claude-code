"""Runtime configuration, loaded from environment variables (and an optional
``.env`` file). Keeping config in one typed object means no module reaches for
``os.environ`` directly — easy to see what's tunable and easy to override
in tests.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ENERGY_TRACKER_",
        env_file=".env",
        extra="ignore",
    )

    # Default source used when an API caller doesn't specify one. "fixture"
    # keeps the app runnable out of the box with no network or key.
    default_source: str = "fixture"

    # EIA API key. Read from EIA_API_KEY *or* ENERGY_TRACKER_EIA_API_KEY.
    eia_api_key: str | None = None

    # Cache time-to-live for service-layer results, in seconds.
    cache_ttl_seconds: int = 300

    # Outbound HTTP timeout for live sources, in seconds.
    http_timeout_seconds: float = 30.0


def load_settings() -> Settings:
    """Build settings, allowing the unprefixed EIA_API_KEY as a convenience."""
    import os

    settings = Settings()
    if settings.eia_api_key is None:
        settings.eia_api_key = os.environ.get("EIA_API_KEY")
    return settings
