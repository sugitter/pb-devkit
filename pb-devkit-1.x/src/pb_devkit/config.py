"""PowerBuilder DevKit - Project Configuration.

Usage:
    Place a .pbdevkit.json or .pbdevkit.yaml file in your project root.
    CLI commands will automatically detect and use it.

    Or specify: python pb.py --config my-config.json analyze ./sources

Example .pbdevkit.json:
{
    "pb_version": 125,
    "max_routine_lines": 150,
    "max_complexity": 15,
    "max_nesting": 3,
    "rules": {
        "enabled": ["fix_empty_catch", "fix_deprecated"],
        "disabled": ["fix_magic_numbers"]
    },
    "naming": {
        "datawindow": "^d_",
        "window": "^w_",
        "menu": "^m_",
        "function": "^(f_|gf_)",
        "userobject": "^(n_|u_)",
        "structure": "^s_"
    },
    "encoding": "gb2312"
}
"""
from __future__ import annotations
import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_FILENAMES = [".pbdevkit.json", "pb-devkit.json"]

# Default configuration values
DEFAULTS = {
    "pb_version": 125,
    "max_routine_lines": 200,
    "max_complexity": 20,
    "max_nesting": 4,
    "encoding": "utf-8",
    "rules": {
        "enabled": None,    # None = all
        "disabled": [],
    },
    "naming": {
        "datawindow": "^d_",
        "window": "^w_",
        "menu": "^m_",
        "function": "^(f_|gf_)",
        "userobject": "^(n_|u_)",
        "structure": "^s_",
    },
}


class PBConfig:
    """Project-level configuration loader and accessor."""

    def __init__(self, data: Optional[dict] = None):
        self._data = deepcopy(DEFAULTS)
        if data:
            self._deep_merge(self._data, data)

    @classmethod
    def load(cls, path: Optional[str] = None) -> PBConfig:
        """Load configuration from a file or auto-detect from project root."""
        if path:
            p = Path(path)
            if not p.exists():
                logger.warning("Config file not found: %s", p)
                return cls()
            return cls._load_file(p)

        # Auto-detect: walk up from CWD
        cwd = Path.cwd()
        for d in [cwd] + list(cwd.parents):
            for name in CONFIG_FILENAMES:
                cfg = d / name
                if cfg.exists():
                    logger.debug("Found config: %s", cfg)
                    return cls._load_file(cfg)

        return cls()

    @classmethod
    def _load_file(cls, path: Path) -> PBConfig:
        """Load and parse a JSON config file."""
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
            logger.debug("Loaded config from %s", path)
            return cls(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load config %s: %s", path, e)
            return cls()

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                PBConfig._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    # Accessors
    @property
    def pb_version(self) -> int:
        return self._data.get("pb_version", 125)

    @property
    def max_routine_lines(self) -> int:
        return self._data.get("max_routine_lines", 200)

    @property
    def max_complexity(self) -> int:
        return self._data.get("max_complexity", 20)

    @property
    def max_nesting(self) -> int:
        return self._data.get("max_nesting", 4)

    @property
    def encoding(self) -> str:
        return self._data.get("encoding", "utf-8")

    @property
    def enabled_rules(self) -> Optional[list[str]]:
        rules = self._data.get("rules", {})
        return rules.get("enabled")

    @property
    def disabled_rules(self) -> list[str]:
        rules = self._data.get("rules", {})
        return rules.get("disabled", [])

    @property
    def naming_patterns(self) -> dict[str, str]:
        return self._data.get("naming", DEFAULTS["naming"])

    def as_analyzer_config(self) -> dict:
        """Return config dict for PBSourceAnalyzer."""
        return {
            "max_routine_lines": self.max_routine_lines,
            "max_complexity": self.max_complexity,
            "max_nesting": self.max_nesting,
        }

    def to_dict(self) -> dict:
        """Return full config as dict."""
        return dict(self._data)
