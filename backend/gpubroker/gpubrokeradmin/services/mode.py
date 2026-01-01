"""
GPUBROKER Mode Service - Legacy Compatibility Layer

This module provides backwards compatibility.
All functionality is now in config.py.

Usage (DEPRECATED):
    from gpubrokeradmin.services.mode import mode_service
    
Usage (NEW - Preferred):
    from gpubrokeradmin.services.config import config
    mode = config.mode.current
"""
from .config import config


class ModeServiceCompat:
    """
    Compatibility wrapper that provides both mode methods
    and config status methods via the same interface.
    """
    
    @property
    def current_mode(self):
        return config.mode.current
    
    @property
    def is_sandbox(self):
        return config.mode.is_sandbox
    
    @property
    def is_live(self):
        return config.mode.is_live
    
    def set_mode(self, mode):
        return config.mode.set(mode)
    
    def get_status(self):
        """Get status from config."""
        return config.get_status()
    
    def get_all_configs(self):
        """Get all configs."""
        return config.get_all()


# Legacy compatibility singleton
mode_service = ModeServiceCompat()
