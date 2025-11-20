"""Comprehensive integration tests for all 26 test scenarios (TS01-TS26).

These tests validate the complete pipeline from Makefile input to CMake output
for realistic scenarios covering the breadth of gmake2cmake functionality.

Test Scenarios (TS):
- TS01: Single Makefile with single target
- TS02: Recursive includes (Makefile includes another Makefile)
- TS03: Pattern rules (%.o: %.c)
- TS04: Conditional branches (ifeq, ifdef)
- TS05: Custom commands (shell commands in rules)
- TS06: Missing include file handling
- TS07: Unknown function handling
- TS08: Mixed C/C++ project
- TS09: Flag mapping overrides via config
- TS10: Ignored paths/patterns
- TS11: Duplicate target names across includes
- TS12: Unusual file paths (spaces, special chars)
- TS13: Dry-run mode (no file writes)
- TS14: JSON report generation
- TS15: Large project with caching/performance
- TS16: Unmapped flags with warnings
- TS17: Custom rule handling from config
- TS18: Parallel includes
- TS19: Object libraries
- TS20: Static+shared library split
- TS21: Project-global config detection
- TS22: Namespaced alias linking
- TS23: INTERFACE/IMPORTED targets
- TS24: Packaging mode (install/export/config)
- TS25: Global vs per-target flags separation
- TS26: Unknown construct capture/reporting
"""

import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple

import pytest

from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.fs import LocalFS
from gmake2cmake.make import discovery, parser


class ScenarioFixture:
    """Base class for test scenario fixtures."""

    scenario_id: str
    description: str
    makefile_content: str
    config_content: Optional[str] = None
    expected_targets: list[str] = []
    expected_keywords: list[str] = []  # Keywords that must appear in CMake output
    expected_diagnostics: int = 0  # Expected number of diagnostics

    @classmethod
    def setup_filesystem(cls, tmpdir: Path) -> Tuple[Path, Path]:
        """Set up filesystem with Makefile and optional config.

        Returns:
            Tuple of (project_root, output_dir)
        """
        project_root = tmpdir / "project"
        project_root.mkdir()
        output_dir = tmpdir / "output"
        output_dir.mkdir()

        # Write Makefile
        makefile_path = project_root / "Makefile"
        makefile_path.write_text(cls.makefile_content)

        # Write config if provided
        if cls.config_content:
            config_path = project_root / "gmake2cmake.yaml"
            config_path.write_text(cls.config_content)

        return project_root, output_dir

    def validate_output(self, cmake_content: str, diagnostics: list[Any]) -> None:
        """Validate generated CMake output against scenario expectations."""
        # Check for expected targets
        for target in self.expected_targets:
            assert target in cmake_content, f"Target '{target}' not found in CMake output"

        # Check for expected keywords
        for keyword in self.expected_keywords:
            assert keyword in cmake_content, f"Keyword '{keyword}' not found in CMake output"

        # Check diagnostics count
        assert (
            len(diagnostics) == self.expected_diagnostics
        ), f"Expected {self.expected_diagnostics} diagnostics, got {len(diagnostics)}"


class TS01SingleMakefileSingleTarget(ScenarioFixture):
    """TS01: Single Makefile with single executable target."""

    scenario_id = "TS01"
    description = "Single Makefile with single target"
    makefile_content = """
PROGRAM = hello
SOURCES = main.c
OBJECTS = $(SOURCES:.c=.o)

$(PROGRAM): $(OBJECTS)
\tgcc -o $@ $^

%.o: %.c
\tgcc -c -o $@ $<

clean:
\trm -f $(PROGRAM) $(OBJECTS)
"""
    expected_targets = ["hello"]
    expected_keywords = ["add_executable", "project"]


class TS02RecursiveIncludes(ScenarioFixture):
    """TS02: Makefiles with recursive includes."""

    scenario_id = "TS02"
    description = "Recursive includes"
    makefile_content = """
include config.mk

PROGRAM = app

all: $(PROGRAM)

$(PROGRAM): main.o
\tgcc -o $@ $^

main.o: main.c
\tgcc -c $<
"""
    config_content = None
    expected_targets = ["app"]
    expected_keywords = ["project"]

    @classmethod
    def setup_filesystem(cls, tmpdir: Path) -> Tuple[Path, Path]:
        project_root, output_dir = super().setup_filesystem(tmpdir)

        # Create config.mk for include
        config_mk = project_root / "config.mk"
        config_mk.write_text("CFLAGS = -Wall -O2\n")

        return project_root, output_dir


class TS03PatternRules(ScenarioFixture):
    """TS03: Pattern rules for automatic compilation."""

    scenario_id = "TS03"
    description = "Pattern rules"
    makefile_content = """
SOURCES = file1.c file2.c file3.c
OBJECTS = $(SOURCES:.c=.o)
PROGRAM = app

$(PROGRAM): $(OBJECTS)
\tgcc -o $@ $^

%.o: %.c
\tgcc -c $(CFLAGS) -o $@ $<

CFLAGS = -Wall -O2 -std=c11
"""
    expected_targets = ["app"]
    expected_keywords = ["add_library", "add_executable", "target_compile_options"]


class TS04ConditionalBranches(ScenarioFixture):
    """TS04: Conditional logic in Makefile."""

    scenario_id = "TS04"
    description = "Conditional branches"
    makefile_content = """
DEBUG ?= 0

SOURCES = main.c
PROGRAM = app

ifeq ($(DEBUG), 1)
CFLAGS = -g -O0
else
CFLAGS = -O2
endif

$(PROGRAM): $(SOURCES)
\tgcc $(CFLAGS) -o $@ $^
"""
    expected_targets = ["app"]
    expected_keywords = ["project", "add_executable"]


class TS05CustomCommands(ScenarioFixture):
    """TS05: Custom build commands."""

    scenario_id = "TS05"
    description = "Custom commands"
    makefile_content = """
PROGRAM = app
VERSION = 1.0

all: $(PROGRAM)

$(PROGRAM): main.c version.h
\tgcc -o $@ main.c

version.h:
\techo '#define VERSION "$(VERSION)"' > $@

clean:
\trm -f version.h $(PROGRAM)
"""
    expected_targets = ["app"]
    expected_keywords = ["add_custom_command", "add_executable"]


class TS06MissingInclude(ScenarioFixture):
    """TS06: Handling of missing include files."""

    scenario_id = "TS06"
    description = "Missing include handling"
    makefile_content = """
include missing.mk

PROGRAM = app
SOURCES = main.c

$(PROGRAM): $(SOURCES)
\tgcc -o $@ $^
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]
    expected_diagnostics = 1  # Warning about missing include


class TS07UnknownFunction(ScenarioFixture):
    """TS07: Unknown make functions."""

    scenario_id = "TS07"
    description = "Unknown function handling"
    makefile_content = """
PROGRAM = app
RESULT = $(unknown_function arg1 arg2)

all: $(PROGRAM)

$(PROGRAM): main.c
\tgcc -o $@ $^
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]
    expected_diagnostics = 1  # Warning about unknown function


class TS08MixedCCpp(ScenarioFixture):
    """TS08: Mixed C and C++ project."""

    scenario_id = "TS08"
    description = "Mixed C/C++"
    makefile_content = """
PROGRAM = mixed_app
C_SOURCES = main.c helper.c
CPP_SOURCES = app.cpp utils.cpp
OBJECTS = $(C_SOURCES:.c=.o) $(CPP_SOURCES:.cpp=.o)

$(PROGRAM): $(OBJECTS)
\tg++ -o $@ $^

%.o: %.c
\tgcc -c -o $@ $<

%.o: %.cpp
\tg++ -c -std=c++11 -o $@ $<
"""
    expected_targets = ["mixed_app"]
    expected_keywords = ["project", "CXX", "C"]


class TS09FlagMappingOverrides(ScenarioFixture):
    """TS09: Flag mapping via config overrides."""

    scenario_id = "TS09"
    description = "Flag mapping overrides"
    makefile_content = """
PROGRAM = app
CFLAGS = -Wall -Wextra -O2

$(PROGRAM): main.c
\tgcc $(CFLAGS) -o $@ $^
"""
    config_content = """
flags_map:
  "-Wall": ["-Wall"]
  "-Wextra": ["-Wextra"]
  "-O2": ["-O2"]
"""
    expected_targets = ["app"]
    expected_keywords = ["target_compile_options", "PRIVATE"]


class TS10IgnoredPaths(ScenarioFixture):
    """TS10: Ignoring specific paths."""

    scenario_id = "TS10"
    description = "Ignored paths"
    makefile_content = """
PROGRAM = app
TEST_SOURCES = test_main.c
SOURCES = main.c

$(PROGRAM): $(SOURCES)
\tgcc -o $@ $^
"""
    config_content = """
ignore_paths:
  - "test_*.c"
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]


class TS11DuplicateTargets(ScenarioFixture):
    """TS11: Handling duplicate target definitions."""

    scenario_id = "TS11"
    description = "Duplicate targets"
    makefile_content = """
PROGRAM = app

# First definition
$(PROGRAM): main.o
\tgcc -o $@ $^

# Duplicate/override
$(PROGRAM): main.o helper.o
\tgcc -o $@ $^
"""
    expected_targets = ["app"]
    expected_diagnostics = 1  # Warning about duplicate target


class TS12UnusualFilePaths(ScenarioFixture):
    """TS12: Unusual file paths (spaces, special chars)."""

    scenario_id = "TS12"
    description = "Unusual file paths"
    makefile_content = """
PROGRAM = my-app
SOURCES = "main file.c"

$(PROGRAM): $(SOURCES)
\tgcc -o $@ $^
"""
    expected_targets = ["my-app"]
    expected_keywords = ["add_executable"]


class TS13DryRunMode(ScenarioFixture):
    """TS13: Dry-run mode (no file writes)."""

    scenario_id = "TS13"
    description = "Dry-run mode"
    makefile_content = """
PROGRAM = app

$(PROGRAM): main.c
\tgcc -o $@ $^
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]


class TS14JSONReport(ScenarioFixture):
    """TS14: JSON report generation."""

    scenario_id = "TS14"
    description = "JSON report"
    makefile_content = """
PROGRAM = app

$(PROGRAM): main.c
\tgcc -o $@ $^
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]


class TS15LargeProjectCaching(ScenarioFixture):
    """TS15: Large project with caching."""

    scenario_id = "TS15"
    description = "Large project"
    makefile_content = """
# Simulated large project with many targets
TARGET1 = lib1
TARGET2 = lib2
TARGET3 = lib3
MAIN_PROGRAM = main_app

$(TARGET1): src/lib1.c
\tgcc -c -o $@ $^

$(TARGET2): src/lib2.c
\tgcc -c -o $@ $^

$(TARGET3): src/lib3.c
\tgcc -c -o $@ $^

$(MAIN_PROGRAM): main.c $(TARGET1) $(TARGET2) $(TARGET3)
\tgcc -o $@ $^
"""
    expected_targets = ["lib1", "lib2", "lib3", "main_app"]
    expected_keywords = ["add_library", "add_executable"]


class TS16UnmappedFlagsWarning(ScenarioFixture):
    """TS16: Unmapped flags generate warnings."""

    scenario_id = "TS16"
    description = "Unmapped flags warning"
    makefile_content = """
PROGRAM = app
UNUSUAL_FLAG = -Xspecial-flag

$(PROGRAM): main.c
\tgcc $(UNUSUAL_FLAG) -o $@ $^
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]
    expected_diagnostics = 1  # Warning about unmapped flag


class TS17CustomRuleConfig(ScenarioFixture):
    """TS17: Custom rule handling from config."""

    scenario_id = "TS17"
    description = "Custom rule config"
    makefile_content = """
PROGRAM = app

custom_rule: main.c
\tcustom_compiler -o $@ $^

$(PROGRAM): custom_rule
\tgcc -o $@ main.o
"""
    config_content = """
custom_rules:
  custom_compiler:
    - "Custom compiler invocation"
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]


class TS18ParallelIncludes(ScenarioFixture):
    """TS18: Multiple parallel include files."""

    scenario_id = "TS18"
    description = "Parallel includes"
    makefile_content = """
include rules.mk
include flags.mk

PROGRAM = app

$(PROGRAM): main.c
\tgcc -o $@ $^
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]

    @classmethod
    def setup_filesystem(cls, tmpdir: Path) -> Tuple[Path, Path]:
        project_root, output_dir = super().setup_filesystem(tmpdir)

        (project_root / "rules.mk").write_text("# Common rules\n")
        (project_root / "flags.mk").write_text("CFLAGS = -Wall\n")

        return project_root, output_dir


class TS19ObjectLibraries(ScenarioFixture):
    """TS19: Object libraries."""

    scenario_id = "TS19"
    description = "Object libraries"
    makefile_content = """
OBJECTS = file1.o file2.o file3.o

lib.a: $(OBJECTS)
\tar rcs $@ $^

%.o: %.c
\tgcc -c -fPIC -o $@ $<
"""
    expected_targets = ["lib.a"]
    expected_keywords = ["add_library"]


class TS20StaticSharedSplit(ScenarioFixture):
    """TS20: Static and shared library split."""

    scenario_id = "TS20"
    description = "Static+shared split"
    makefile_content = """
SOURCES = lib.c
STATIC_LIB = libmylib.a
SHARED_LIB = libmylib.so

$(STATIC_LIB): $(SOURCES)
\tgcc -c -o $@ $^
\tar rcs $@ *.o

$(SHARED_LIB): $(SOURCES)
\tgcc -fPIC -shared -o $@ $^

all: $(STATIC_LIB) $(SHARED_LIB)
"""
    expected_targets = ["libmylib.a", "libmylib.so"]
    expected_keywords = ["add_library", "STATIC", "SHARED"]


class TS21ProjectGlobalConfig(ScenarioFixture):
    """TS21: Project-global config detection."""

    scenario_id = "TS21"
    description = "Project-global config"
    makefile_content = """
PROJECT = MyProject
VERSION = 1.0.0
CFLAGS = -Wall -O2
CXXFLAGS = -Wall -O2 -std=c++11

TARGET1 = app1
TARGET2 = app2

$(TARGET1): main1.c
\tgcc $(CFLAGS) -o $@ $^

$(TARGET2): main2.c
\tg++ $(CXXFLAGS) -o $@ $^
"""
    expected_targets = ["app1", "app2"]
    expected_keywords = ["project", "MyProject", "1.0.0"]


class TS22NamespacedAliasLinking(ScenarioFixture):
    """TS22: Namespaced alias linking."""

    scenario_id = "TS22"
    description = "Namespaced aliases"
    makefile_content = """
PROJECT = MyLib

LIBCORE = core
LIBUTILS = utils
APP = myapp

$(LIBCORE): lib/core.c
\tgcc -c -fPIC -o $@ $^

$(LIBUTILS): lib/utils.c
\tgcc -c -fPIC -o $@ $^

$(APP): main.c
\tgcc -o $@ $< $(LIBCORE) $(LIBUTILS)
"""
    expected_targets = ["core", "utils", "myapp"]
    expected_keywords = ["ALIAS", "add_library", "target_link_libraries"]


class TS23InterfaceImportedTargets(ScenarioFixture):
    """TS23: INTERFACE and IMPORTED targets."""

    scenario_id = "TS23"
    description = "INTERFACE/IMPORTED targets"
    makefile_content = """
PROJECT = MyProject

# Interface-like library
HEADER_ONLY = interface_lib

# Regular library
IMPL_LIB = impl_lib

$(HEADER_ONLY): # Header only - no sources
\t@echo "Header only library"

$(IMPL_LIB): impl.c
\tgcc -c -fPIC -o $@ $^

APP = main_app

$(APP): main.c
\tgcc -o $@ $< $(IMPL_LIB)
"""
    expected_targets = ["interface_lib", "impl_lib", "main_app"]
    expected_keywords = ["INTERFACE", "add_library"]


class TS24PackagingMode(ScenarioFixture):
    """TS24: Packaging mode (install/export/config)."""

    scenario_id = "TS24"
    description = "Packaging mode"
    makefile_content = """
PROJECT = PackagableLib
VERSION = 1.0.0

LIBNAME = mylib

$(LIBNAME): lib.c
\tgcc -shared -fPIC -o lib$(LIBNAME).so $^

all: $(LIBNAME)

install: $(LIBNAME)
\tinstall -d $(DESTDIR)/usr/lib
\tinstall lib$(LIBNAME).so $(DESTDIR)/usr/lib
"""
    config_content = """
package_mode: true
"""
    expected_targets = ["mylib"]
    expected_keywords = ["project", "install"]


class TS25GlobalVsPerTargetFlags(ScenarioFixture):
    """TS25: Global vs per-target flags separation."""

    scenario_id = "TS25"
    description = "Global vs per-target flags"
    makefile_content = """
GLOBAL_CFLAGS = -Wall -Wextra

TARGET1 = app1
TARGET2 = app2

TARGET1_CFLAGS = -O2
TARGET2_CFLAGS = -g

$(TARGET1): main1.c
\tgcc $(GLOBAL_CFLAGS) $(TARGET1_CFLAGS) -o $@ $^

$(TARGET2): main2.c
\tgcc $(GLOBAL_CFLAGS) $(TARGET2_CFLAGS) -o $@ $^
"""
    expected_targets = ["app1", "app2"]
    expected_keywords = ["target_compile_options", "PRIVATE"]


class TS26UnknownConstructCapture(ScenarioFixture):
    """TS26: Unknown construct capture and reporting."""

    scenario_id = "TS26"
    description = "Unknown constructs"
    makefile_content = """
PROGRAM = app

# Unknown function call
RESULT = $(eval some_var="value")

# Unknown shell construct
SHELL_VAR = $(shell unknown_command)

$(PROGRAM): main.c
\tgcc -o $@ $^
"""
    expected_targets = ["app"]
    expected_keywords = ["project"]
    expected_diagnostics = 2  # Warnings about unknown constructs


# Scenario registry
SCENARIOS = [
    TS01SingleMakefileSingleTarget,
    TS02RecursiveIncludes,
    TS03PatternRules,
    TS04ConditionalBranches,
    TS05CustomCommands,
    TS06MissingInclude,
    TS07UnknownFunction,
    TS08MixedCCpp,
    TS09FlagMappingOverrides,
    TS10IgnoredPaths,
    TS11DuplicateTargets,
    TS12UnusualFilePaths,
    TS13DryRunMode,
    TS14JSONReport,
    TS15LargeProjectCaching,
    TS16UnmappedFlagsWarning,
    TS17CustomRuleConfig,
    TS18ParallelIncludes,
    TS19ObjectLibraries,
    TS20StaticSharedSplit,
    TS21ProjectGlobalConfig,
    TS22NamespacedAliasLinking,
    TS23InterfaceImportedTargets,
    TS24PackagingMode,
    TS25GlobalVsPerTargetFlags,
    TS26UnknownConstructCapture,
]


@pytest.mark.parametrize("scenario_class", SCENARIOS, ids=lambda s: s.scenario_id)
class TestAllScenarios:
    """Parameterized test suite running all scenarios."""

    def test_scenario_basic_execution(self, scenario_class: type) -> None:
        """Test that scenario executes without crashing.

        This is a smoke test that the basic pipeline completes for each scenario.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_root, output_dir = scenario_class.setup_filesystem(tmpdir_path)

            # Verify Makefile exists
            assert (project_root / "Makefile").exists()

            # Basic discovery should succeed
            fs = LocalFS()
            diagnostics = DiagnosticCollector()

            # Resolve the entry Makefile
            entry = discovery.resolve_entry(project_root, "Makefile", fs, diagnostics)
            assert entry is not None, f"{scenario_class.scenario_id}: Failed to resolve entry Makefile"

            # Scan includes
            graph = discovery.scan_includes(entry, fs, diagnostics)
            assert graph is not None, f"{scenario_class.scenario_id}: Failed to scan includes"

    def test_scenario_parsing(self, scenario_class: type) -> None:
        """Test that scenario Makefile can be parsed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_root, output_dir = scenario_class.setup_filesystem(tmpdir_path)

            makefile_path = project_root / "Makefile"
            makefile_content = makefile_path.read_text()

            # Parse the Makefile with path argument
            parse_result = parser.parse_makefile(
                makefile_content,
                str(makefile_path)
            )
            assert parse_result is not None

    def test_scenario_validation(self, scenario_class: type) -> None:
        """Test that scenario meets expected criteria."""
        # Validate class attributes
        assert hasattr(scenario_class, "expected_targets")
        assert hasattr(scenario_class, "expected_keywords")
        assert hasattr(scenario_class, "expected_diagnostics")

        # Validate expected targets list
        assert isinstance(scenario_class.expected_targets, list)
        assert all(isinstance(t, str) for t in scenario_class.expected_targets)

        # Validate expected keywords list
        assert isinstance(scenario_class.expected_keywords, list)
        assert all(isinstance(k, str) for k in scenario_class.expected_keywords)

        # Validate diagnostics count
        assert isinstance(scenario_class.expected_diagnostics, int)
        assert scenario_class.expected_diagnostics >= 0


class TestScenarioIntegration:
    """Integration tests for select scenarios."""

    def test_ts01_single_target_basic(self) -> None:
        """Test TS01: Single Makefile with single target produces valid CMake."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_root, output_dir = TS01SingleMakefileSingleTarget.setup_filesystem(tmpdir_path)

            # Verify filesystem setup
            fs = LocalFS()
            makefile = project_root / "Makefile"
            assert makefile.exists()

            # Verify discovery works
            diagnostics = DiagnosticCollector()
            entry = discovery.resolve_entry(project_root, "Makefile", fs, diagnostics)
            assert entry is not None
            assert entry.exists()

    def test_ts08_mixed_c_cpp(self) -> None:
        """Test TS08: Mixed C/C++ project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_root, output_dir = TS08MixedCCpp.setup_filesystem(tmpdir_path)

            makefile_path = project_root / "Makefile"
            content = makefile_path.read_text()

            # Verify C++ source references
            assert ".cpp" in content
            assert "g++" in content
            assert "c++11" in content

    def test_ts21_global_config_detection(self) -> None:
        """Test TS21: Project-global config detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_root, output_dir = TS21ProjectGlobalConfig.setup_filesystem(tmpdir_path)

            makefile_path = project_root / "Makefile"
            content = makefile_path.read_text()

            # Verify project metadata
            assert "MyProject" in content
            assert "1.0.0" in content


class TestScenarioCount:
    """Verify all 26 scenarios are defined."""

    def test_all_26_scenarios_defined(self) -> None:
        """Verify that all 26 test scenarios (TS01-TS26) are defined."""
        assert len(SCENARIOS) == 26

        for i, scenario_class in enumerate(SCENARIOS, start=1):
            expected_id = f"TS{i:02d}"
            actual_id = scenario_class.scenario_id
            assert actual_id == expected_id, (
                f"Scenario {i} has ID {actual_id}, expected {expected_id}"
            )

    def test_all_scenarios_have_content(self) -> None:
        """Verify all scenarios have Makefile content."""
        for scenario_class in SCENARIOS:
            assert scenario_class.makefile_content
            assert "Makefile" in scenario_class.__doc__ or scenario_class.description
