"""Backward-compatible authentication imports."""

from app.api.dependencies import get_current_api_key

__all__ = ["get_current_api_key"]
