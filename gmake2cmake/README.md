## Module Layout

- `constants/`: All shared defaults and enumerations (CLI defaults, valid types, report filenames).
- `types/`: Shared `TypedDict` definitions (e.g., diagnostics payloads).
- `adapters/`: Boundaries to external systems.
  - `adapters/filesystem.py`: Exposes filesystem interfaces and context managers.
  - `adapters/cmake/`: Exposes CMake emission entry points.
- `config.py`, `make/`, `ir/`, `cmake/`: Core domain logic.
- `fs.py`, `security.py`, `path_utils.py`: Low-level utilities used by adapters and core.

Adapters collect IO-facing behaviors so core logic can stay pure and testable. Constants and types are centralized to avoid duplication and circular imports.
