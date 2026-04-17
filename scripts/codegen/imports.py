"""Per-module import accumulator.

`ImportSet` collects imports during emission and renders them into a single
source block. Final ordering is left to ruff's import sorter — we only group
by kind (`import X` / `from typing` / `from X import Y`) so the rendered file
is deterministic before ruff runs.
"""

from __future__ import annotations


class ImportSet:
    """Collects `import ...` / `from X import Y` entries for a module."""

    def __init__(self) -> None:
        self._stdlib: set[tuple[str, str]] = set()  # (module, symbol)
        self._typing: set[str] = set()
        self._from: dict[str, set[str]] = {}  # module -> set of symbols
        self._raw_modules: set[str] = set()  # `import X`

    def add_stdlib(self, module: str, symbol: str) -> None:
        self._stdlib.add((module, symbol))

    def add_typing(self, symbol: str) -> None:
        self._typing.add(symbol)

    def add_from(self, module: str, symbol: str) -> None:
        self._from.setdefault(module, set()).add(symbol)

    def add_import(self, module: str) -> None:
        self._raw_modules.add(module)

    def render(self) -> str:
        blocks: list[str] = []
        raw_modules = sorted(self._raw_modules | {m for m, _ in self._stdlib})
        if raw_modules:
            blocks.append("\n".join(f"import {m}" for m in raw_modules))
        if self._typing:
            blocks.append("from typing import " + ", ".join(sorted(self._typing)))
        ordered_from = sorted(self._from.items())
        if ordered_from:
            lines = [
                f"from {module} import {', '.join(sorted(symbols))}"
                for module, symbols in ordered_from
            ]
            blocks.append("\n".join(lines))
        return "\n\n".join(b for b in blocks if b)
