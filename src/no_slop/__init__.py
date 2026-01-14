from no_slop._version import __version__
from no_slop.flake8_plugin import SlopStyleChecker
from no_slop.mypy_plugin import NoSlopPlugin

__all__ = ["NoSlopPlugin", "SlopStyleChecker", "UnusedDefaultsChecker", "__version__"]


def __getattr__(name: str) -> type:
    """Lazy import for UnusedDefaultsChecker to avoid import cycle when running as __main__."""
    if name == "UnusedDefaultsChecker":
        from no_slop.unused_defaults import UnusedDefaultsChecker

        return UnusedDefaultsChecker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
