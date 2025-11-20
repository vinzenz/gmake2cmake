# gmake2cmake

CLI tool to convert GNU Make projects into CMake builds.

## Quick start
- Install (dev): `pip install -e .[dev]`
- Run conversion: `gmake2cmake --source-dir . --dry-run`
- Enable packaging outputs: add `--with-packaging`
- Target a specific Makefile: `gmake2cmake --source-dir . -f Makefile.custom`

## Notes
- Python >=3.11; lint with `ruff check .` and test with `pytest`.
- Architecture overview lives in `Architecture.md`; components are under `gmake2cmake/`.
