"""Phase 4 matrix_writer DISP branch -- render correctness + dispatch order.

Smoke test (RED gate) -- replaced by the full suite in Task 2.
"""
from __future__ import annotations


def test_matrix_writer_disp_public_api_imports() -> None:
    """Smoke test: the new helpers must be importable from matrix_writer."""
    from subsideo.validation.matrix_writer import (
        _is_disp_cell_shape,
        _render_disp_cell,
    )

    assert _is_disp_cell_shape is not None
    assert _render_disp_cell is not None
