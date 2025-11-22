from __future__ import annotations

from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.introspection_parser import IntrospectionData, ParsedTarget
from gmake2cmake.introspection_reconcile import reconcile
from gmake2cmake.ir.builder import Project, ProjectGlobalConfig, Target


def _project_with_target(name: str) -> Project:
    tgt = Target(
        artifact=f"{name}.a",
        name=name,
        alias=None,
        type="static",
        sources=[],
        include_dirs=[],
        defines=[],
        compile_options=[],
        link_options=[],
        link_libs=[],
        deps=[],
        custom_commands=[],
        visibility=None,
    )
    return Project(
        name="proj",
        version=None,
        namespace="proj",
        languages=["C"],
        targets=[tgt],
        project_config=ProjectGlobalConfig(vars={}, flags={}, defines=[], includes=[], feature_toggles={}, sources=[]),
    )


def test_reconcile_marks_validated_when_matching():
    proj = _project_with_target("foo")
    data = IntrospectionData(targets={"foo": ParsedTarget(name="foo", prerequisites=[], commands=[])}, variables={})
    diagnostics = DiagnosticCollector()
    updated = reconcile(proj, data, diagnostics)
    target = updated.targets[0]
    assert target.validated_by_introspection is True
    assert not diagnostics.diagnostics


def test_reconcile_updates_deps_and_records_mismatch():
    proj = _project_with_target("foo")
    data = IntrospectionData(
        targets={"foo": ParsedTarget(name="foo", prerequisites=["dep"], commands=["echo build"])},
        variables={},
    )
    diagnostics = DiagnosticCollector()
    updated = reconcile(proj, data, diagnostics)
    target = updated.targets[0]
    assert target.deps == ["dep"]
    assert target.introspection_commands == ["echo build"]
    assert any(d.code == "INTROSPECTION_MISMATCH" for d in diagnostics.diagnostics)


def test_reconcile_adds_introspection_only_targets():
    proj = _project_with_target("foo")
    data = IntrospectionData(
        targets={"bar": ParsedTarget(name="bar", prerequisites=["x"], commands=["echo x"])},
        variables={},
    )
    diagnostics = DiagnosticCollector()
    updated = reconcile(proj, data, diagnostics)
    names = {t.name for t in updated.targets}
    assert {"foo", "bar"} == names
    bar = next(t for t in updated.targets if t.name == "bar")
    assert bar.origin == "introspection"
    assert bar.validated_by_introspection is True
