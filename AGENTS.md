# Repository Guidelines

## Project Structure & Module Organization
- `gmake2cmake/`: Python sources (cli, config, diagnostics, fs, make/* for discovery/parser/evaluator, ir/*, cmake/*).
- `tests/`: Pytest suites (unit, emitter/ir, e2e) plus `conftest.py` with `FakeFS`.
- `docs/`: Architecture wiki and component guides; root `Architecture.md` mirrors design.
- `tasks/`: Active tasks live here; completed tasks must move to `tasks/archive/` (Golden Rule). `whats-next.md` lists upcoming work.

## Build, Test, and Development Commands
- Install dev deps: `pip install -e .[dev]`.
- Run tests: `pytest` (config in `pyproject.toml`); e2e smoke lives in `tests/e2e/`.
- Lint: `ruff check .` (line length 100, py311 target).
- Dry-run CLI example: `python -m gmake2cmake.cli --source-dir . --dry-run`.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, prefer type hints and dataclasses for data containers.
- Keep internal paths posix-normalized; avoid sys.exit in library code.
- Aliases/namespace per architecture (`Project::Target`), but keep file names snake_case.
- Use ruff defaults plus import sorting; target deterministic ordering in outputs.

## Testing Guidelines
- Framework: pytest. Tests live under `tests/` mirroring module names; e.g., `test_config_manager.py`, `tests/ir/`, `tests/emitter/`, `tests/e2e/`.
- Add unit tests per function/class spec; add golden or fixture-based checks for emitter output where relevant.
- Run `pytest` locally before PRs; include dry-run/e2e coverage for new pipeline behavior.

## Commit & Pull Request Guidelines
- Commit messages: concise imperative (“Add emitter packaging hooks”). Group related changes; avoid mixing refactors and features without note.
- Use `git commit -s` (Signed-off-by) for all commits. Initial state already committed; every finished task needs its own signed-off commit.
- PRs should describe scope, testing (`pytest`, `ruff`), and link to tasks/issues. Include expected outputs for CMake generation changes when possible.
- After completing a task, move its file to `tasks/archive/` and add new tasks derived from `whats-next.md` as needed.

## Architecture Overview (Quick)
- Pipeline: CLI → ConfigManager → Discoverer → Parser → Evaluator → IRBuilder → CMakeEmitter → DiagnosticsReporter.
- Global config centralized (config.mk/rules.mk/defs.mk recognized), internal libs get namespaced aliases, packaging optional via `--with-packaging`.
