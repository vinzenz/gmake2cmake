from __future__ import annotations

from pathlib import Path

import pytest

from gmake2cmake import config
from gmake2cmake.diagnostics import DiagnosticCollector, has_errors
from tests.conftest import FakeFS


def test_load_missing_config_adds_error():
    fs = FakeFS()
    diagnostics = DiagnosticCollector()
    data = config.load_yaml(Path("missing.yaml"), fs=fs, diagnostics=diagnostics)
    assert data == {}
    assert has_errors(diagnostics) is True


def test_unknown_key_strict_and_non_strict():
    diagnostics = DiagnosticCollector()
    model = config.parse_model({"project_name": "p", "foo": "bar"}, strict=False, diagnostics=diagnostics)
    assert model.project_name == "p"
    assert has_errors(diagnostics) is False

    diagnostics = DiagnosticCollector()
    model = config.parse_model({"foo": "bar"}, strict=True, diagnostics=diagnostics)
    assert has_errors(diagnostics) is True
    assert model.project_name is None


def test_flag_mapping_and_dedup():
    diagnostics = DiagnosticCollector()
    model = config.parse_model({"flag_mappings": {"-O2": "-O3"}}, strict=False, diagnostics=diagnostics)
    mapped, unmapped = config.apply_flag_mapping(["-O2", "-O2", "-Wall"], model)
    assert mapped == ["-O3", "-Wall"]
    assert unmapped == ["-Wall"]


def test_ignore_paths_glob():
    diagnostics = DiagnosticCollector()
    model = config.parse_model({"ignore_paths": ["src/generated/*"]}, strict=False, diagnostics=diagnostics)
    assert config.should_ignore_path("src/generated/file.c", model)
    assert not config.should_ignore_path("src/other/file.c", model)


def test_global_config_files_default_and_override():
    diagnostics = DiagnosticCollector()
    model = config.parse_model({}, strict=False, diagnostics=diagnostics)
    assert model.global_config_files == ["config.mk", "rules.mk", "defs.mk"]
    diagnostics = DiagnosticCollector()
    model = config.parse_model({"global_config_files": ["root.mk"]}, strict=False, diagnostics=diagnostics)
    assert model.global_config_files == ["root.mk"]


def test_link_overrides_validation_and_classification():
    diagnostics = DiagnosticCollector()
    model = config.parse_model({"link_overrides": {"foo": {"classification": "internal"}}}, strict=False, diagnostics=diagnostics)
    override = config.classify_library_override("foo", model)
    assert override is not None
    assert override.classification == "internal"

    diagnostics = DiagnosticCollector()
    model = config.parse_model({"link_overrides": {"bar": {"classification": "bad"}}}, strict=True, diagnostics=diagnostics)
    assert has_errors(diagnostics) is True


def test_target_mapping_validation():
    # Valid mapping
    tm = config.TargetMapping(src_name="mylib", dest_name="mylib_output")
    assert tm.src_name == "mylib"

    # Invalid: empty src_name
    with pytest.raises(ValueError, match="src_name cannot be empty"):
        config.TargetMapping(src_name="", dest_name="output")

    # Invalid: empty dest_name
    with pytest.raises(ValueError, match="dest_name cannot be empty"):
        config.TargetMapping(src_name="mylib", dest_name="")

    # Invalid: bad type_override
    with pytest.raises(ValueError, match="Invalid type_override"):
        config.TargetMapping(src_name="lib", dest_name="out", type_override="bad_type")

    # Invalid: bad visibility
    with pytest.raises(ValueError, match="Invalid visibility"):
        config.TargetMapping(src_name="lib", dest_name="out", visibility="BADVIS")

    # Valid: with proper type and visibility
    tm = config.TargetMapping(
        src_name="mylib",
        dest_name="output",
        type_override="static",
        visibility="PUBLIC",
    )
    assert tm.type_override == "static"
    assert tm.visibility == "PUBLIC"

    # Valid: interface type
    tm = config.TargetMapping(
        src_name="iface",
        dest_name="iface_out",
        type_override="interface",
    )
    assert tm.type_override == "interface"


def test_custom_rule_config_validation():
    # Valid rule
    rule = config.CustomRuleConfig(match="pattern", handler="handler_fn")
    assert rule.match == "pattern"

    # Invalid: empty match
    with pytest.raises(ValueError, match="match cannot be empty"):
        config.CustomRuleConfig(match="", handler="handler")

    # Invalid: empty handler
    with pytest.raises(ValueError, match="handler cannot be empty"):
        config.CustomRuleConfig(match="pattern", handler="")


def test_link_override_validation():
    # Valid override
    override = config.LinkOverride(classification="internal")
    assert override.classification == "internal"

    # Invalid: empty classification
    with pytest.raises(ValueError, match="classification cannot be empty"):
        config.LinkOverride(classification="")

    # Invalid: bad classification
    with pytest.raises(ValueError, match="Invalid classification"):
        config.LinkOverride(classification="unknown")
