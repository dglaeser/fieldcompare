"""Version information for fieldcompare"""
from importlib import metadata

try:
    __version__ = metadata.version("fieldcompare")
except Exception:
    __version__ = "unknown"
