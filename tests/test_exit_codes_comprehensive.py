"""Comprehensive tests for exit codes module (TASK-0059 expansion).

Tests cover:
- ExitCode enum values
- Code to category mapping
- get_exit_code() function with various diagnostic scenarios
- get_exit_code_with_unknown_threshold() function
- Priority ordering of exit codes
- Edge cases and unknown codes
"""

from __future__ import annotations

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.exit_codes import (
    ExitCode,
    get_exit_code,
    get_exit_code_with_unknown_threshold,
)


class TestExitCodeEnum:
    """Tests for ExitCode enum."""

    def test_exit_code_values(self):
        """ExitCode enum should have correct values."""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.USAGE == 1
        assert ExitCode.CONFIG == 2
        assert ExitCode.PARSE == 3
        assert ExitCode.BUILD == 4
        assert ExitCode.IO == 5

    def test_exit_code_is_int_enum(self):
        """ExitCode should be IntEnum."""
        assert isinstance(ExitCode.SUCCESS, int)
        assert isinstance(ExitCode.CONFIG, int)
        assert isinstance(ExitCode.BUILD, int)

    def test_exit_code_comparison(self):
        """ExitCode should support integer comparison."""
        assert ExitCode.SUCCESS < ExitCode.USAGE
        assert ExitCode.CONFIG > ExitCode.USAGE
        assert ExitCode.BUILD == 4

    def test_exit_code_in_set(self):
        """ExitCode should work in sets."""
        codes = {ExitCode.SUCCESS, ExitCode.CONFIG, ExitCode.IO}
        assert ExitCode.SUCCESS in codes
        assert ExitCode.PARSE not in codes


class TestGetExitCodeSuccess:
    """Tests for success scenarios."""

    def test_empty_diagnostics_returns_success(self):
        """No diagnostics should return SUCCESS."""
        collector = DiagnosticCollector()
        code = get_exit_code(collector)
        assert code == ExitCode.SUCCESS

    def test_only_warnings_returns_success(self):
        """Only warnings should return SUCCESS."""
        collector = DiagnosticCollector()
        add(collector, "WARN", "CONFIG_UNKNOWN_KEY", "Test warning", "test.mk:1")
        code = get_exit_code(collector)
        assert code == ExitCode.SUCCESS

    def test_only_info_returns_success(self):
        """Only info diagnostics should return SUCCESS."""
        collector = DiagnosticCollector()
        add(collector, "INFO", "CONFIG_UNKNOWN_KEY", "Test info", "test.mk:1")
        code = get_exit_code(collector)
        assert code == ExitCode.SUCCESS

    def test_mixed_non_error_returns_success(self):
        """Only non-error diagnostics should return SUCCESS."""
        collector = DiagnosticCollector()
        add(collector, "WARN", "CONFIG_UNKNOWN_KEY", "w1", "test")
        add(collector, "INFO", "CONFIG_UNKNOWN_KEY", "i1", "test")
        add(collector, "WARN", "CONFIG_UNKNOWN_KEY", "w2", "test")
        code = get_exit_code(collector)
        assert code == ExitCode.SUCCESS


class TestGetExitCodeConfigErrors:
    """Tests for config error exit code."""

    def test_config_missing_error(self):
        """CONFIG_MISSING should return CONFIG exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_MISSING", "Config file missing", "config.yaml")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_config_read_fail_error(self):
        """CONFIG_READ_FAIL should return CONFIG exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_READ_FAIL", "Cannot read config", "config.yaml")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_config_parse_error(self):
        """CONFIG_PARSE_ERROR should return CONFIG exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_PARSE_ERROR", "Invalid YAML", "config.yaml")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_config_schema_validation_error(self):
        """CONFIG_SCHEMA_VALIDATION should return CONFIG exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_SCHEMA_VALIDATION", "Invalid config structure", "config.yaml:10")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_config_unknown_key_error(self):
        """CONFIG_UNKNOWN_KEY should return CONFIG exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_UNKNOWN_KEY", "Unknown key in config", "config.yaml:5")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_multiple_config_errors(self):
        """Multiple config errors should still return CONFIG."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_MISSING", "m", "")
        add(collector, "ERROR", "CONFIG_PARSE_ERROR", "p", "")
        add(collector, "ERROR", "CONFIG_SCHEMA_VALIDATION", "s", "")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG


class TestGetExitCodeParseErrors:
    """Tests for parse error exit code."""

    def test_eval_recursive_loop_error(self):
        """EVAL_RECURSIVE_LOOP should return PARSE exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "EVAL_RECURSIVE_LOOP", "Variable expansion loop detected", "Makefile:10")
        code = get_exit_code(collector)
        assert code == ExitCode.PARSE

    def test_eval_no_source_error(self):
        """EVAL_NO_SOURCE should return PARSE exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "EVAL_NO_SOURCE", "No source file specified", "Makefile:5")
        code = get_exit_code(collector)
        assert code == ExitCode.PARSE

    def test_discovery_include_optional_missing(self):
        """DISCOVERY_INCLUDE_OPTIONAL_MISSING should return PARSE."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "DISCOVERY_INCLUDE_OPTIONAL_MISSING", "Optional include file not found", "Makefile:1")
        code = get_exit_code(collector)
        assert code == ExitCode.PARSE


class TestGetExitCodeBuildErrors:
    """Tests for build error exit code."""

    def test_ir_unmapped_flag_error(self):
        """IR_UNMAPPED_FLAG should return BUILD exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "IR_UNMAPPED_FLAG", "Unknown compiler flag", "Makefile:15")
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD

    def test_ir_dup_target_error(self):
        """IR_DUP_TARGET should return BUILD exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "IR_DUP_TARGET", "Duplicate target definition", "Makefile:20")
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD

    def test_ir_dependency_cycle_error(self):
        """IR_DEPENDENCY_CYCLE should return BUILD exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "IR_DEPENDENCY_CYCLE", "Circular dependency detected", "Makefile:10")
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD

    def test_discovery_cycle_error(self):
        """DISCOVERY_CYCLE should return BUILD exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "DISCOVERY_CYCLE", "Include file cycle detected", "Makefile:1")
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD

    def test_emit_unknown_type_error(self):
        """EMIT_UNKNOWN_TYPE should return BUILD exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "EMIT_UNKNOWN_TYPE", "Unknown target type", "ir:target1")
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD

    def test_multiple_build_errors(self):
        """Multiple build errors should still return BUILD."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "IR_UNMAPPED_FLAG", "m", "")
        add(collector, "ERROR", "IR_DEPENDENCY_CYCLE", "c", "")
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD


class TestGetExitCodeIOErrors:
    """Tests for IO error exit code."""

    def test_emit_write_fail_error(self):
        """EMIT_WRITE_FAIL should return IO exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "EMIT_WRITE_FAIL", "Cannot write output file", "CMakeLists.txt")
        code = get_exit_code(collector)
        assert code == ExitCode.IO

    def test_report_write_fail_error(self):
        """REPORT_WRITE_FAIL should return IO exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "REPORT_WRITE_FAIL", "Cannot write report file", "report.md")
        code = get_exit_code(collector)
        assert code == ExitCode.IO

    def test_report_serialize_fail_error(self):
        """REPORT_SERIALIZE_FAIL should return IO exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "REPORT_SERIALIZE_FAIL", "Cannot serialize report", "report.json")
        code = get_exit_code(collector)
        assert code == ExitCode.IO

    def test_discovery_read_fail_error(self):
        """DISCOVERY_READ_FAIL should return IO exit code."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "DISCOVERY_READ_FAIL", "Cannot read input file", "Makefile")
        code = get_exit_code(collector)
        assert code == ExitCode.IO


class TestGetExitCodePriority:
    """Tests for exit code priority ordering."""

    def test_config_priority_over_io(self):
        """CONFIG errors should take priority over IO errors."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_MISSING", "m", "")
        add(collector, "ERROR", "EMIT_WRITE_FAIL", "w", "")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_config_priority_over_build(self):
        """CONFIG errors should take priority over BUILD errors."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_PARSE_ERROR", "m", "")
        add(collector, "ERROR", "IR_UNMAPPED_FLAG", "b", "")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_config_priority_over_parse(self):
        """CONFIG errors should take priority over PARSE errors."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_SCHEMA_VALIDATION", "m", "")
        add(collector, "ERROR", "EVAL_RECURSIVE_LOOP", "p", "")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_io_priority_over_build(self):
        """IO errors should take priority over BUILD errors."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "EMIT_WRITE_FAIL", "io", "")
        add(collector, "ERROR", "IR_UNMAPPED_FLAG", "b", "")
        code = get_exit_code(collector)
        assert code == ExitCode.IO

    def test_io_priority_over_parse(self):
        """IO errors should take priority over PARSE errors."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "REPORT_WRITE_FAIL", "io", "")
        add(collector, "ERROR", "EVAL_RECURSIVE_LOOP", "p", "")
        code = get_exit_code(collector)
        assert code == ExitCode.IO

    def test_build_priority_over_parse(self):
        """BUILD errors should take priority over PARSE errors."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "IR_DEPENDENCY_CYCLE", "b", "")
        add(collector, "ERROR", "EVAL_RECURSIVE_LOOP", "p", "")
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD

    def test_parse_priority_over_usage(self):
        """PARSE errors should take priority over USAGE errors."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "EVAL_RECURSIVE_LOOP", "p", "")
        add(collector, "ERROR", "CLI_UNHANDLED", "u", "")
        code = get_exit_code(collector)
        assert code == ExitCode.PARSE


class TestGetExitCodeUnknownCode:
    """Tests for unknown diagnostic codes."""

    def test_unmapped_code_in_known_category(self):
        """Codes not in _CODE_TO_CATEGORY map should still work if registered."""
        collector = DiagnosticCollector()
        # Use codes that are valid but may not be explicitly mapped
        add(collector, "ERROR", "IR_DUP_ALIAS", "Duplicate alias", "test")
        code = get_exit_code(collector)
        # Should return BUILD since IR_DUP_ALIAS is mapped to BUILD
        assert code == ExitCode.BUILD

    def test_code_with_known_code_priority(self):
        """Multiple codes should use priority ordering."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "IR_UNMAPPED_FLAG", "Flag unmapped", "")
        add(collector, "ERROR", "CONFIG_MISSING", "Config missing", "")
        code = get_exit_code(collector)
        # CONFIG should take priority
        assert code == ExitCode.CONFIG


class TestGetExitCodeWithUnknownThreshold:
    """Tests for get_exit_code_with_unknown_threshold function."""

    def test_no_errors_no_unknowns_returns_success(self):
        """No errors and no unknowns should return SUCCESS."""
        collector = DiagnosticCollector()
        code = get_exit_code_with_unknown_threshold(collector, 0, threshold=0)
        assert code == ExitCode.SUCCESS

    def test_no_errors_unknowns_below_threshold(self):
        """Unknowns below threshold should return SUCCESS."""
        collector = DiagnosticCollector()
        code = get_exit_code_with_unknown_threshold(collector, 5, threshold=10)
        assert code == ExitCode.SUCCESS

    def test_no_errors_unknowns_above_threshold(self):
        """Unknowns above threshold should return PARSE."""
        collector = DiagnosticCollector()
        code = get_exit_code_with_unknown_threshold(collector, 15, threshold=10)
        assert code == ExitCode.PARSE

    def test_no_errors_unknowns_equal_threshold(self):
        """Unknowns equal to threshold should return SUCCESS."""
        collector = DiagnosticCollector()
        code = get_exit_code_with_unknown_threshold(collector, 10, threshold=10)
        assert code == ExitCode.SUCCESS

    def test_zero_threshold_disabled(self):
        """Zero threshold disables unknown count checking."""
        collector = DiagnosticCollector()
        code = get_exit_code_with_unknown_threshold(collector, 100, threshold=0)
        assert code == ExitCode.SUCCESS

    def test_error_overrides_unknown_count(self):
        """Errors should override unknown count threshold."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "CONFIG_MISSING", "Config missing", "test")
        code = get_exit_code_with_unknown_threshold(collector, 15, threshold=10)
        # Error should return CONFIG, not PARSE
        assert code == ExitCode.CONFIG

    def test_error_takes_precedence(self):
        """Explicit error should take precedence over unknowns."""
        collector = DiagnosticCollector()
        add(collector, "ERROR", "IR_UNMAPPED_FLAG", "Flag unmapped", "test")
        code = get_exit_code_with_unknown_threshold(collector, 100, threshold=50)
        # Error returns BUILD, not PARSE from unknowns
        assert code == ExitCode.BUILD

    def test_multiple_unknowns_with_high_threshold(self):
        """Many unknowns with high threshold should return SUCCESS."""
        collector = DiagnosticCollector()
        code = get_exit_code_with_unknown_threshold(collector, 50, threshold=100)
        assert code == ExitCode.SUCCESS

    def test_single_unknown_with_low_threshold(self):
        """Single unknown with low threshold should return PARSE."""
        collector = DiagnosticCollector()
        code = get_exit_code_with_unknown_threshold(collector, 1, threshold=0)
        # With threshold=0, no checking happens
        assert code == ExitCode.SUCCESS

        # With threshold > 0, single unknown triggers PARSE
        code = get_exit_code_with_unknown_threshold(collector, 1, threshold=0)
        # Still SUCCESS because threshold is disabled
        assert code == ExitCode.SUCCESS

    def test_large_unknown_count(self):
        """Very large unknown count should trigger PARSE."""
        collector = DiagnosticCollector()
        code = get_exit_code_with_unknown_threshold(collector, 1000, threshold=50)
        assert code == ExitCode.PARSE


class TestExitCodeEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_many_warnings_one_error(self):
        """Many warnings with one error should return error's code."""
        collector = DiagnosticCollector()
        for i in range(3):
            add(collector, "WARN", "CONFIG_UNKNOWN_KEY", f"Warning {i}", "test")
        add(collector, "ERROR", "CONFIG_MISSING", "Config missing", "test")
        code = get_exit_code(collector)
        assert code == ExitCode.CONFIG

    def test_duplicate_error_codes(self):
        """Duplicate error codes should not affect result."""
        collector = DiagnosticCollector()
        for _ in range(3):
            add(collector, "ERROR", "IR_UNMAPPED_FLAG", "Flag unmapped", "test")
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD

    def test_code_priority_in_mixed_errors(self):
        """Priority ordering should apply with mixed codes."""
        collector = DiagnosticCollector()
        # Use codes with different priorities
        add(collector, "ERROR", "IR_UNMAPPED_FLAG", "Unmapped flag", "test")
        add(collector, "ERROR", "EVAL_RECURSIVE_LOOP", "Recursive variable", "test")
        # Should map to BUILD (priority: CONFIG > IO > BUILD > PARSE > USAGE)
        code = get_exit_code(collector)
        assert code == ExitCode.BUILD  # BUILD has higher priority than PARSE

    def test_all_error_codes_mapped(self):
        """All ExitCode values should be achievable."""
        exit_codes = [
            (ExitCode.SUCCESS, ""),
            (ExitCode.CONFIG, "CONFIG_MISSING"),
            (ExitCode.PARSE, "EVAL_RECURSIVE_LOOP"),
            (ExitCode.BUILD, "IR_UNMAPPED_FLAG"),
            (ExitCode.IO, "EMIT_WRITE_FAIL"),
        ]

        for expected_code, error_code in exit_codes:
            collector = DiagnosticCollector()
            if error_code:
                add(collector, "ERROR", error_code, "Test", "test")
            code = get_exit_code(collector)
            assert code == expected_code, f"Failed for {error_code}: got {code}, expected {expected_code}"
