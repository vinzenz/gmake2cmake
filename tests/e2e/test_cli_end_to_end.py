from __future__ import annotations

from gmake2cmake import cli
from tests.conftest import FakeFS


def test_end_to_end_minimal(tmp_path):
    fs = FakeFS()
    makefile = tmp_path / "Makefile"
    fs.store[makefile] = "all: main.o\n\tcc -c main.c -o main.o\n"
    exit_code = cli.run(["--source-dir", str(tmp_path), "--dry-run"], fs=fs)
    assert exit_code == 0
