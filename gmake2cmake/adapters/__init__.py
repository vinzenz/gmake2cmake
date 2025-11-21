"""Adapter layer for external integrations (filesystem, CMake, etc.).

This package exposes thin adapter modules that wrap external systems while
keeping core domain logic isolated from IO concerns.
"""

__all__ = ["filesystem", "cmake"]
