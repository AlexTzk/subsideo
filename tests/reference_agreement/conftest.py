"""Fixtures + linter for reference_agreement tests.

Per GATE-04 + PITFALLS Pitfall 6: tests in this tree MUST NOT assert any
criteria.py threshold. This conftest walks the AST of each collected test
module and flags `assert X <op> <numeric_literal>` as a collection error.

Plumbing-style assertions (np.isfinite, `is True`, `is None`, len checks,
isinstance, string equality) are allowed.

v1.1 solo-dev enforcement: no pre-commit hook, no external CI linter --
the conftest fails loudly at pytest collection time if a reviewer forgot
the discipline.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _scan(src: str, filename: str) -> list[str]:
    """Return human-readable descriptions of disallowed asserts."""
    try:
        tree = ast.parse(src, filename=filename)
    except SyntaxError as e:
        return [f"{filename}:{e.lineno}: SyntaxError: {e.msg}"]

    bad: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        if isinstance(test, ast.Compare):
            comparands = [test.left, *test.comparators]
            for c in comparands:
                if (
                    isinstance(c, ast.Constant)
                    and isinstance(c.value, (int, float))
                    and not isinstance(c.value, bool)
                ):
                    bad.append(
                        f"{filename}:{node.lineno}: assert has numeric-literal "
                        f"comparand {c.value!r} -- reference_agreement tests must "
                        f"not assert criteria.py thresholds"
                    )
                    break
    return bad


def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Fail fast if any collected reference_agreement test asserts a threshold."""
    scanned: set[Path] = set()
    violations: list[str] = []
    for item in items:
        fspath = Path(str(item.fspath))
        try:
            rel = fspath.relative_to(Path(config.rootpath))
        except ValueError:
            continue
        if not str(rel).startswith("tests/reference_agreement/"):
            continue
        if fspath in scanned:
            continue
        scanned.add(fspath)
        violations.extend(_scan(fspath.read_text(), str(rel)))

    if violations:
        msg = (
            "\n".join(violations)
            + "\n\nMove threshold assertions to tests/product_quality/ -- "
              "reference_agreement tests must assert plumbing only (GATE-04)."
        )
        # pytest.exit guarantees a non-zero exit code that CI / developers see.
        pytest.exit(msg, returncode=4)
