"""Phase 4 prepare_for_reference adapter — 12-cell method×form matrix + DISP-05 no-write-back.

Plan 04-02 RED test: this file initially imports the new public API
(``prepare_for_reference``, ``ReferenceGridSpec``, ``MultilookMethod``) which
does not yet exist on ``subsideo.validation.compare_disp``. Importing therefore
raises ``ImportError`` and the smoke test below fails. Plan 04-02 Task 1 GREEN
adds the implementation; Plan 04-02 Task 2 expands this file to the full
17-test matrix (3 error-path + 12 method-x-form + 1 no-write-back + 1 spot-check).
"""
from __future__ import annotations


def test_public_api_exports() -> None:
    """RED smoke test: prepare_for_reference + ReferenceGridSpec + MultilookMethod
    must be importable from subsideo.validation.compare_disp.
    """
    from subsideo.validation.compare_disp import (  # noqa: F401
        MultilookMethod,
        ReferenceGridSpec,
        prepare_for_reference,
    )

    assert prepare_for_reference is not None
    assert ReferenceGridSpec is not None
