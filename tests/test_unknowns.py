from __future__ import annotations

from gmake2cmake.ir.unknowns import UnknownConstructFactory, to_dict


def test_unknown_construct_factory_assigns_ids_and_truncates():
    factory = UnknownConstructFactory()
    long_snippet = "X" * 200
    uc1 = factory.create(category="make_function", file="Makefile", raw_snippet=long_snippet, normalized_form=None, impact={"severity": "warning"})
    uc2 = factory.create(category="shell_command", file="Makefile", raw_snippet="$(shell echo hi)", normalized_form="shell(echo hi)")

    assert uc1.id == "UC0001"
    assert uc2.id == "UC0002"
    assert len(uc1.raw_snippet) <= 160
    assert uc1.normalized_form == uc1.raw_snippet  # fallback when normalized_form missing
    assert uc2.normalized_form.startswith("shell(")
    dto = to_dict(uc2)
    assert dto["id"] == "UC0002"
    assert dto["category"] == "shell_command"
