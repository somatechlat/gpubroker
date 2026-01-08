"""
Legacy API module now delegates to the unified config.api instance.
"""
from config.api import api

__all__ = ["api"]
