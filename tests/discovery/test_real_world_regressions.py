"""Regression fixtures that mirror diagnostics seen on real-world projects."""

from __future__ import annotations

from pathlib import Path

from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.make import discovery
from tests.conftest import FakeFS


def _has_code(diags: DiagnosticCollector, code: str) -> bool:
    return any(d.code == code for d in diags.diagnostics)


def test_template_only_project_triggers_entry_missing() -> None:
    """Binutils/OpenSSL ship Makefile.in templates but no generated Makefile."""
    fs = FakeFS()
    project_root = Path("/src/binutils")
    fs.store[project_root / "Makefile.in"] = "# configure template"
    fs.store[project_root / "Makefile.tpl"] = "# autotools template"

    diagnostics = DiagnosticCollector()
    entry = discovery.resolve_entry(project_root, None, fs, diagnostics)

    assert entry is None
    assert _has_code(diagnostics, "DISCOVERY_ENTRY_MISSING")


def test_recursive_make_backedge_flags_cycle() -> None:
    """Git's t/Makefile and t/perf/Makefile recurse into each other."""
    fs = FakeFS()
    root = Path("/git/t/Makefile")
    perf = Path("/git/t/perf/Makefile")
    fs.store[root] = "all:\n\t$(MAKE) -C perf\n"
    fs.store[perf] = "all:\n\t$(MAKE) -C .. test-lint\n"

    diagnostics = DiagnosticCollector()
    discovery.scan_includes(root, fs, diagnostics)

    assert _has_code(diagnostics, "DISCOVERY_CYCLE")


def test_conditional_wildcard_includes_reported_missing() -> None:
    """Git's computed dependency includes surface as missing files."""
    fs = FakeFS()
    root = Path("/git/Makefile")
    fs.store[root] = (
        "dep_files := $(wildcard *.d)\n"
        "dep_files_present := $(wildcard $(dep_files))\n"
        "ifneq ($(dep_files_present),)\n"
        "include $(dep_files_present)\n"
        "endif\n"
    )

    diagnostics = DiagnosticCollector()
    discovery.scan_includes(root, fs, diagnostics)

    assert _has_code(diagnostics, "DISCOVERY_INCLUDE_MISSING")


def test_kbuild_autoconf_rule_misparsed_and_read_fails() -> None:
    """BusyBox lines starting with 'include/' are treated as include directives."""
    fs = FakeFS()
    root = Path("/busybox/Makefile")
    fs.store[root] = (
        "-include .config\n"
        "include/autoconf.h: .kconfig.d .config $(wildcard $(srctree)/*/*.c) "
        "$(wildcard $(srctree)/*/*/*.c) | gen_build_files\n"
    )

    diagnostics = DiagnosticCollector()
    discovery.discover(root.parent, None, fs, diagnostics)

    assert _has_code(diagnostics, "DISCOVERY_INCLUDE_OPTIONAL_MISSING")
    assert _has_code(diagnostics, "DISCOVERY_INCLUDE_MISSING")
    assert _has_code(diagnostics, "DISCOVERY_READ_FAIL")


def test_make_dash_c_comment_triggers_subdir_missing_warning() -> None:
    """Git's QUIET_SUBDIR placeholder misparses '-C # comment' as a subdir."""
    fs = FakeFS()
    root = Path("/git/shared.mak")
    fs.store[root] = "QUIET_SUBDIR0 = +$(MAKE) -C # space to separate -C and subdir\n"

    diagnostics = DiagnosticCollector()
    discovery.scan_includes(root, fs, diagnostics)

    assert _has_code(diagnostics, "DISCOVERY_SUBDIR_MISSING")
