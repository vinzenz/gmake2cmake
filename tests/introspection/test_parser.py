from __future__ import annotations

from gmake2cmake.introspection_parser import IntrospectionData, parse_dump


def test_parse_simple_dump():
    dump = """# Files
foo: bar baz
\tcc -c foo.c

# Variables
CFLAGS = -O2
"""
    result = parse_dump(dump)
    assert isinstance(result, IntrospectionData)
    assert "foo" in result.targets
    foo = result.targets["foo"]
    assert foo.prerequisites == ["bar", "baz"]
    assert foo.commands == ["cc -c foo.c"]
    assert result.variables["CFLAGS"] == "-O2"


def test_parse_phony_targets():
    dump = """# Files
.PHONY: clean all
clean:
\trm -f *.o
all: foo

    # Variables
    """
    result = parse_dump(dump)
    assert result.targets["clean"].phony is True
    assert result.targets["all"].phony is True


def test_parse_ignores_builtin_section():
    dump = """# Files
foo: bar

# Built-in
target: builtin
"""
    result = parse_dump(dump)
    assert "target" not in result.targets
    assert "foo" in result.targets
