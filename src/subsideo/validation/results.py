"""Generic result types for product-quality vs reference-agreement split.

Per-product ValidationResult classes in src/subsideo/products/types.py
COMPOSE these two types (D-07). Import direction is
products/types.py -> validation/results.py (one-way; data-only leaf; no
products/* or validation/compare_* imports allowed here).

Per D-08: named measurements dict + criterion_ids list; NO stored bools.
Pass/fail computed at read time via evaluate() -- keeps old metrics.json
records re-evaluable against edited criteria thresholds (drift-safe).

Per Open Question 3: missing measurement raises KeyError (fail-fast),
matching D-09 big-bang philosophy. matrix_writer.py (Plan 01-09) catches
this and surfaces 'MEASUREMENT MISSING' in the cell.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from subsideo.validation.criteria import CRITERIA, Criterion


@dataclass
class ProductQualityResult:
    """Product-quality gate measurements + criterion IDs.

    NEVER holds a .passed bool. Use evaluate() at read time.
    """

    measurements: dict[str, float] = field(default_factory=dict)
    criterion_ids: list[str] = field(default_factory=list)


@dataclass
class ReferenceAgreementResult:
    """Reference-agreement measurements + criterion IDs.

    NEVER holds a .passed bool. Use evaluate() at read time.
    """

    measurements: dict[str, float] = field(default_factory=dict)
    criterion_ids: list[str] = field(default_factory=list)


_COMPARATORS: dict[str, Callable[[float, float], bool]] = {
    ">":  lambda a, b: float(a) > float(b),
    ">=": lambda a, b: float(a) >= float(b),
    "<":  lambda a, b: float(a) < float(b),
    "<=": lambda a, b: float(a) <= float(b),
}


def measurement_key(criterion_id: str) -> str:
    """Convert 'rtc.rmse_db_max' -> 'rmse_db' (last dot-segment, strip _min/_max).

    PUBLIC helper (exported in validation/__init__.py __all__) -- matrix_writer
    (Plan 01-08) reuses this instead of duplicating the stripping rule, so a
    single source-of-truth determines how criterion IDs map to measurement
    dict keys.
    """
    last = criterion_id.rsplit(".", 1)[-1]
    if last.endswith("_min"):
        return last[: -len("_min")]
    if last.endswith("_max"):
        return last[: -len("_max")]
    return last


def evaluate(
    result: ProductQualityResult | ReferenceAgreementResult,
    criteria: dict[str, Criterion] | None = None,
) -> dict[str, bool]:
    """Return {criterion_id: passed_bool} for every criterion listed on `result`.

    Never mutates `result`. Read-time computation keeps old metrics.json
    records re-evaluable against edited criteria.py thresholds.

    Raises
    ------
    KeyError
        If a criterion_id is not in `criteria`, or if its measurement key is
        not in result.measurements (fail-fast per Open Question 3).
    """
    if criteria is None:
        criteria = CRITERIA

    out: dict[str, bool] = {}
    for cid in result.criterion_ids:
        if cid not in criteria:
            raise KeyError(f"Criterion ID {cid!r} not in criteria registry")
        crit = criteria[cid]
        mkey = measurement_key(cid)
        if mkey not in result.measurements:
            raise KeyError(
                f"Criterion {cid!r} requires measurement {mkey!r} but only "
                f"{list(result.measurements)} are present"
            )
        op = _COMPARATORS[crit.comparator]
        out[cid] = bool(op(result.measurements[mkey], crit.threshold))
    return out
