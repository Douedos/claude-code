"""Energy Consumption Tracker — normalized US electricity demand data.

Layering (outer depends on inner, never the reverse):

    api  →  service  →  registry  →  sources/*  →  models

Add a new feed by writing one ``DemandSource`` subclass and registering it.
"""

__version__ = "0.1.0"
