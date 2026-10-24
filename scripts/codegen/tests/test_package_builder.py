from __future__ import annotations

from pathlib import Path

import pytest

from scripts.codegen.ir import EmittedClass, EmittedField
from scripts.codegen.package_builder import (
    DEFAULT_PACKAGE_VERSION,
    _escape_string_literal,
    _render_class,
    _render_field,
    development_status,
    resolve_package_version,
)


def test_resolve_package_version_explicit_wins(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0-beta.3"\n')
    assert resolve_package_version(tmp_path, "2.0.0") == "2.0.0"


def test_resolve_package_version_keeps_existing(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0-beta.3"\n')
    assert resolve_package_version(tmp_path, None) == "0.1.0-beta.3"


def test_resolve_package_version_defaults_for_new_package(tmp_path: Path) -> None:
    assert resolve_package_version(tmp_path, None) == DEFAULT_PACKAGE_VERSION


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.1.0-alpha.1", "3 - Alpha"),
        ("0.0.0.dev0", "3 - Alpha"),
        ("0.1.0-beta.3", "4 - Beta"),
        ("0.1.0rc1", "4 - Beta"),
        ("1.0.0", "5 - Production/Stable"),
    ],
)
def test_development_status(version: str, expected: str) -> None:
    assert development_status(version) == expected


def test_escape_string_literal_escapes_quotes_and_backslashes() -> None:
    assert _escape_string_literal('the "name" field') == 'the \\"name\\" field'
    assert _escape_string_literal("C:\\Users\\x") == "C:\\\\Users\\\\x"


def test_render_class_docstring_ending_in_quote_compiles() -> None:
    """A definition description ending in a quote must not produce four
    consecutive quotes where the docstring closes."""
    cls = EmittedClass(
        class_name="Foo", bases=[], docstring='the field "name"', fields=[]
    )
    source = _render_class(cls)
    compile(source, "<test>", "exec")
    ns: dict[str, object] = {}
    exec(source, {"BaseK8sModel": object}, ns)
    assert ns["Foo"].__doc__ == 'the field "name"'


def test_render_class_docstring_with_backslash_is_preserved_literally() -> None:
    """A backslash in the description must not be silently reinterpreted as
    an escape sequence (e.g. turning a literal ``\\n`` into a real newline)."""
    cls = EmittedClass(
        class_name="Bar", bases=[], docstring="path like C:\\Users\\x", fields=[]
    )
    source = _render_class(cls)
    compile(source, "<test>", "exec")
    ns: dict[str, object] = {}
    exec(source, {"BaseK8sModel": object}, ns)
    assert ns["Bar"].__doc__ == "path like C:\\Users\\x"


def test_render_field_description_ending_in_quote_compiles() -> None:
    field = EmittedField(
        python_name="name",
        alias="name",
        type_expression="str",
        required=True,
        description='the field "name"',
    )
    source = "from pydantic import Field\n\n\nclass Foo:\n" + _render_field(
        field, "Foo"
    )
    compile(source, "<test>", "exec")
