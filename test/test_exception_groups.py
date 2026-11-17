"""``raise_single()``: a task group's only exception, raised as it was."""

from __future__ import annotations

import pytest

from kubex.core.exception_groups import raise_single


@pytest.mark.parametrize(
    "context", [None, KeyError("context")], ids=["no-context", "context"]
)
def test_raises_the_only_exception_with_its_cause_and_context(
    context: BaseException | None,
) -> None:
    cause = ValueError("cause")
    error = RuntimeError("failed")
    error.__cause__ = cause
    error.__context__ = context
    with pytest.raises(RuntimeError) as raised:
        try:
            raise ExceptionGroup("one", [error])
        except ExceptionGroup as errors:
            raise_single(errors)
    assert raised.value is error
    assert error.__cause__ is cause
    # not chained to the group it was caught in
    assert error.__context__ is context


def test_returns_when_there_are_several() -> None:
    errors = ExceptionGroup("two", [ValueError("a"), KeyError("b")])
    assert raise_single(errors) is None  # type: ignore[func-returns-value]
