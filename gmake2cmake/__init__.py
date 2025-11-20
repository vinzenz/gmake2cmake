"""gmake2cmake: A Make to CMake translation utility.

This package provides tools for analyzing Makefiles and generating equivalent CMake configurations.
Primary entry points are through submodules:
  - gmake2cmake.cli: Command-line interface
  - gmake2cmake.config: Configuration management
  - gmake2cmake.ir: Intermediate representation building
  - gmake2cmake.cmake: CMake file emission
"""

__all__ = [
    "cli",
    "config",
    "diagnostics",
    "fs",
]
