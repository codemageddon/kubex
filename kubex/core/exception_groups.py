"""Exceptions out of a task group.

anyio's task groups raise what their tasks raise as an exception group, even
when only one task failed. ``raise_single()`` gives that one exception back to
the caller as it was raised, its ``__cause__`` and ``__context__`` included.
"""

from __future__ import annotations


def raise_single(errors: BaseExceptionGroup[BaseException]) -> None:
    """Raises the exception of `errors` when it is the only one, as it was
    raised; returns otherwise.

    Call it in the `except` clause that caught `errors`. There, `raise error`
    would chain the exception to the group and `raise error from None` would
    erase its own cause, so its `__context__` is put back on the way out.
    """
    if len(errors.exceptions) != 1:
        return
    error = errors.exceptions[0]
    context = error.__context__
    try:
        raise error
    finally:
        error.__context__ = context
