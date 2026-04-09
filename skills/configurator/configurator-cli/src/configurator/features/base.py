"""Base class and types for feature plugins."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class FeatureMeta:
    """Static metadata about a feature plugin."""

    id: str
    label: str
    version: str
    order: int
    dependencies: list[str] = field(default_factory=list)
    group: str | None = None


class Feature(abc.ABC):
    """Base class that every feature plugin must implement."""

    @abc.abstractmethod
    def meta(self) -> FeatureMeta:
        """Return static metadata for this feature."""

    # ── Web editor ────────────────────────────────────────────

    @abc.abstractmethod
    def config_html(self, ctx: RenderContext) -> str:
        """Return the HTML fragment for this feature's section."""

    @abc.abstractmethod
    def config_js_read(self) -> str:
        """Return JS that reads this feature's form fields into ``cfg``."""

    @abc.abstractmethod
    def config_js_populate(self) -> str:
        """Return JS that populates this feature's form fields from ``CONFIG``."""

    @abc.abstractmethod
    def config_js_update_disabled(self) -> str:
        """Return JS for controlling field enable/disable state."""

    # ── Config manipulation ───────────────────────────────────

    @abc.abstractmethod
    def default_config(self) -> dict | list:
        """Return the default config for a new project."""

    @abc.abstractmethod
    def manifest_to_config(self, manifest: dict) -> dict | list:
        """Extract this feature's config from a deployed manifest."""

    @abc.abstractmethod
    def deployed_keys(self, manifest: dict) -> set[str]:
        """Return which of this feature's keys are deployed."""

    def validate(self, feature_cfg: dict | list, full_cfg: dict) -> list[str]:
        """Validate this feature's config. Return list of error strings."""
        return []


@dataclass
class RenderContext:
    """Context passed to config_html() for conditional rendering."""

    deployed_keys: set[str]
    urls: dict[str, str]
    live_domains: set[str]
    config: dict
