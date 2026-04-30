# Phase 7: Results Matrix + Release Readiness - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 6 (new/modified)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `eval-rtc/metrics.json` | config/data | transform | `eval-dist/metrics.json` | exact |
| `eval-rtc/meta.json` | config/data | transform | `eval-dist/meta.json` + `eval-rtc-eu/meta.json` | exact |
| `src/subsideo/validation/matrix_writer.py` | utility | transform | self (extend existing dispatch) | exact |
| `src/subsideo/validation/criteria.py` | config | read-only | self (no changes needed) | exact |
| `docs/validation_methodology.md` | documentation | append-only | self (§1–§5 structure) | exact |
| `CHANGELOG.md` | documentation | append | self (existing v0.1.0 entry) | exact |

---

## Pattern Assignments

### `eval-rtc/metrics.json` (new DEFERRED sidecar)

**Analog:** `eval-dist/metrics.json` (lines 1–18)

**Exact DEFERRED sidecar format** (`eval-dist/metrics.json`, all 18 lines):
```json
{
  "schema_version": 1,
  "product_quality": {
    "measurements": {},
    "criterion_ids": []
  },
  "reference_agreement": {
    "measurements": {},
    "criterion_ids": []
  },
  "criterion_ids_applied": [],
  "runtime_conda_list_hash": null,
  "cell_status": "DEFERRED",
  "reference_source": "none",
  "cmr_probe_outcome": "operational_not_found",
  "reference_granule_id": null,
  "deferred_reason": "Phase 5 scope amendment..."
}
```

**Required field changes for RTC:NAM:**
- `cell_status`: `"DEFERRED"` (same)
- `reference_source`: `"none"` (same)
- `cmr_probe_outcome`: omit or set to `"n/a"` — RTC:NAM has no CMR probe; the discriminator `_is_dist_nam_shape` keys on `reference_source + cmr_probe_outcome`, so RTC:NAM must NOT include both these fields or it will be routed to `_render_dist_nam_deferred_cell` instead of the new RTC:NAM DEFERRED branch
- `deferred_reason`: `"v1.1 N.Am. RTC eval script (run_eval.py) not migrated to v1.1 harness sidecars; EU RTC (Phase 2) was the v1.1 focus. Unblock: migrate run_eval.py to validation.harness (bounds_for_burst + metrics.json + meta.json write) and re-run N.Am. RTC eval (v1.2)."`
- `unblock_condition`: `"v1.2 N.Am. RTC re-run"` — this field is referenced in CONTEXT.md D-01 and D-02; add it as a top-level key (not present in dist:nam sidecar, but required for the new RTC:NAM renderer)

**Discriminator strategy for the new RTC:NAM branch:**
The existing discriminators key on schema-specific fields (`per_burst`, `per_aoi`, `ramp_attribution`, `per_event`, `reference_source+cmr_probe_outcome`, `selected_aoi+candidates_attempted`, `thresholds_used+loocv_gap`). The new RTC:NAM DEFERRED sidecar must use a unique discriminator field — use `"unblock_condition"` as the key (present only in the RTC:NAM sidecar).

---

### `eval-rtc/meta.json` (new, minimal)

**Analog:** `eval-dist/meta.json` (all 9 lines) + `eval-rtc-eu/meta.json` (18 lines)

**Minimal hand-written meta.json format** (`eval-dist/meta.json`):
```json
{
  "schema_version": 1,
  "git_sha": "14862f72749b0f5289720d0538f4d53479bd74bc",
  "git_dirty": true,
  "run_started_iso": "2026-04-26T04:06:41.931511+00:00",
  "run_duration_s": 6.691257953643799,
  "python_version": "3.12.13",
  "platform": "macOS-26.3.1-arm64-arm-64bit",
  "input_hashes": {}
}
```

For Phase 7, `input_hashes` is `{}` (no new inputs processed; sidecar is written by hand). `git_sha` must be the current HEAD SHA at write time (use `git rev-parse HEAD`). `run_duration_s` can be `0.0` for a hand-authored sidecar. `git_dirty` will typically be `true` during Phase 7 work.

---

### `src/subsideo/validation/matrix_writer.py` (extend dispatch + CALIBRATING annotation)

**Analog:** self — extend the existing dispatch chain in `write_matrix()` and the `_render_measurement()` helper.

#### Task 1: New `_is_rtc_nam_deferred_shape` discriminator

**Pattern:** copy the `_is_dist_nam_shape` discriminator (lines 464–498) as the structural template. Key on the `unblock_condition` field which is unique to the RTC:NAM sidecar.

```python
def _is_rtc_nam_deferred_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json carries the RTC:NAM DEFERRED shape (Phase 7).

    Discriminator: presence of ``unblock_condition`` key in raw JSON. This field
    is unique to the RTC:NAM DEFERRED sidecar and structurally disjoint from all
    other cell schemas (per_burst, per_aoi, ramp_attribution, per_event,
    reference_source+cmr_probe_outcome, selected_aoi+candidates_attempted,
    thresholds_used+loocv_gap).
    """
    import json as _json
    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_rtc_nam_deferred_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "unblock_condition" in raw
```

#### Task 2: New `_render_rtc_nam_deferred_cell` renderer

**Pattern:** copy `_render_dist_nam_deferred_cell` (lines 570–602) as structural template.

```python
def _render_rtc_nam_deferred_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render the rtc:nam DEFERRED cell (Phase 7 D-01 / D-02).

    pq_col: '—' (no product-quality gate).
    ra_col: 'DEFERRED — <unblock_condition>' where unblock_condition is read
    from the sidecar. Consistent with dist:nam DEFERRED rendering pattern but
    without the CMR probe outcome suffix.
    """
    import json as _json
    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.warning(
            "Failed to read deferred rtc:nam metrics from {}: {}", metrics_path, e
        )
        return None
    unblock = raw.get("unblock_condition", "see deferred_reason field")
    pq_col = "—"
    ra_col = f"DEFERRED — {unblock}"
    return pq_col, ra_col
```

#### Task 3: Dispatch insertion point in `write_matrix()`

**Pattern:** insert the new branch at the TOP of the dispatch chain (before the DISP branch at line 711), because the RTC:NAM file is currently missing entirely (causes RUN_FAILED in the default path). Insertion order follows the invariant "new branches go AFTER the last established branch that uses a structurally-disjoint discriminator." The `unblock_condition` discriminator is disjoint from all existing discriminators, so insertion position is flexible. Insert BEFORE the DISP branch for clarity, citing the ordering comment convention.

```python
# Phase 7 RTC:NAM DEFERRED branch: metrics.json with an ``unblock_condition`` key.
# Inserted BEFORE disp:* per Phase 7 D-01 (RTC:NAM was missing entirely;
# adding the branch before the ordered chain avoids any discriminator collision).
if metrics_path.exists() and _is_rtc_nam_deferred_shape(metrics_path):
    cols = _render_rtc_nam_deferred_cell(metrics_path)
    if cols is not None:
        pq_col, ra_col = cols
        lines.append(
            f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
            f"{_escape_table_cell(ra_col)} |"
        )
        continue
    # Fall through to default rendering on parse failure.
```

#### Task 4: CALIBRATING `binds v1.2` annotation in `_render_measurement()`

**Current pattern** (lines 86–91): verdict is `f"{verdict} (CALIBRATING)"` for CALIBRATING criteria.

**Target pattern** (D-05): verdict becomes `f"{verdict} (CALIBRATING — binds {milestone})"` where `milestone = crit.binding_after_milestone`.

The `Criterion.binding_after_milestone` field is already present in `criteria.py` (lines 45–46). The `_render_measurement` function already calls `CRITERIA.get(cid)` and reads `crit.type`. The one-line change:

```python
# Current (line 90):
    if crit.type == "CALIBRATING":
        verdict = f"{verdict} (CALIBRATING)"

# New:
    if crit.type == "CALIBRATING":
        milestone = crit.binding_after_milestone or "future milestone"
        verdict = f"{verdict} (CALIBRATING — binds {milestone})"
```

**DISP-specific annotation** (D-06): DISP CALIBRATING cells also appear in `_render_disp_cell()` (line 429) where the PQ column is hardcoded as `f"*{pq_body} (CALIBRATING)*{warn}"`. The `(CALIBRATING)` suffix there is a direct string literal independent of `_render_measurement`. Apply the same `— binds v1.2` pattern there too, plus the "needs 3rd AOI" note for DISP:

```python
# Current (line 429 in _render_disp_cell):
    pq_col = f"*{pq_body} (CALIBRATING)*{warn}"

# New (DISP-specific, needs 3rd AOI before binding):
    pq_col = f"*{pq_body} (CALIBRATING — needs 3rd AOI before binding; see DISP_UNWRAPPER_SELECTION_BRIEF.md)*{warn}"
```

For CSLC, the CALIBRATING text is emitted via `_render_cslc_selfconsist_cell` (lines 295–296, 346) through the `status_label` string `"X/N CALIBRATING"` and the `f"*{pq_body}*{warn}"` wrapper. The `— binds v1.2` annotation should be appended to the `status_label` string:

```python
# In _render_cslc_selfconsist_cell, after building status_label:
    status_label = ", ".join(tags)
    # Phase 7: append binding milestone (D-05)
    status_label += " — binds v1.2"
```

---

### `src/subsideo/validation/criteria.py` (read-only — no code changes)

**Pattern:** `binding_after_milestone` field on `Criterion` dataclass (lines 45–46):
```python
binding_after_milestone: str | None
```

CALIBRATING criteria that have `binding_after_milestone="v1.2"`:
- `cslc.selfconsistency.coherence_min` (line 119)
- `cslc.selfconsistency.residual_mm_yr_max` (line 129)
- `disp.selfconsistency.coherence_min` (line 161)
- `disp.selfconsistency.residual_mm_yr_max` (line 168)

No edits to `criteria.py` in Phase 7. The `matrix_writer` reads `binding_after_milestone` from existing `Criterion` objects via `crit.binding_after_milestone`.

---

### `docs/validation_methodology.md` (append §6 + §7 + TOC + consistency pass)

**Analog:** self — existing §1 and §4.3 set the structural and voice pattern.

#### Structural voice pattern (from §1)

Every section follows: `TL;DR → structural argument → policy statement → code pointer → diagnostic evidence appendix`

**Section header with anchor** (lines 17–19):
```markdown
## 1. CSLC cross-version phase impossibility

<a name="cross-version-phase"></a>
```

**TL;DR block** (line 21): single bold sentence.

**Policy statement** (lines 59–79): "Do NOT re-attempt with additional corrections." followed by explicit merge-gate language.

**Code pointer** (lines 101–107): references the specific module + function + criterion IDs.

#### §6 content grounding — `harness.select_opera_frame_by_utc_hour()`

**Function signature** (`harness.py` lines 350–355):
```python
def select_opera_frame_by_utc_hour(
    sensing_datetime: datetime,
    frame_metadata: Sequence[dict[str, Any]],
    *,
    tolerance_hours: float = 1.0,
) -> dict[str, Any]:
```

**Docstring rationale** (`harness.py` lines 357–364): "Used when `asf-search` returns multiple candidate OPERA frames for the same burst — the correct frame is the one whose `sensing_datetime` (exact UTC hour + spatial footprint) matches the source SLC."

**Policy statement scope for §6**: "any eval script that selects an OPERA reference without UTC-hour + footprint matching is producing invalid reference-agreement numbers" (CONTEXT.md D-04).

**Cross-reference table update** (§2.6 lines 240–241): stale forward-reference reads "Phase 4 harness-first discipline will document" — Phase 7 updates this to "§6 documents".

#### §7 content grounding — EFFIS cross-sensor precision-first framing

**Existing §4.3 content** (lines 435–465) already covers the class-definition mismatch caveat at the implementation level. §7 is the methodology-level framing that §4.3 points back to.

**Key evidence from `effis.py`** (lines 1–30, 415–432 of validation_methodology.md):
- EFFIS REST API returns *post-event* consolidated perimeters (days-to-weeks after fire)
- DIST-S1 flags *first-detection* active disturbance signal
- Dual rasterise: `all_touched=False` (primary, gate) vs `all_touched=True` (diagnostic)
- EFFIS is fire-only; DIST-S1 flags wildfire + clear-cut + other surface disturbances

**Policy statement for §7**: "cross-sensor evaluation results that show recall < 0.50 but precision > 0.70 are reported as 'precision-first constraint satisfied; recall gap attributed to temporal class-definition mismatch (EFFIS final extent vs DIST first-detection)' — not as unqualified FAIL" (CONTEXT.md D-04 §7).

**Cross-reference**: §7 cross-references §4.3 explicitly for implementation-level evidence.

**Cross-reference table update** (§2.6 line 241): stale "Phase 5 will append" → "§7 documents".

#### TOC pattern (prepend before §1)

Format: list items with markdown anchor links. Anchor names already set in existing sections (`cross-version-phase` at line 19, `multilook-method` at line 251, `dswe-recalibration-methodology` at line 518). Phase 7 must also add anchors to §4 and §7.

```markdown
## Table of Contents

1. [CSLC cross-version phase impossibility](#cross-version-phase)
2. [Product-quality vs reference-agreement distinction](#pq-vs-ra)
3. [DISP comparison-adapter design — multilook method choice](#multilook-method)
4. [DIST-S1 Validation Methodology](#dist-methodology)
5. [DSWE F1 ceiling, held-out Balaton, and threshold-module design](#dswe-recalibration-methodology)
6. [OPERA frame selection by exact UTC hour + spatial footprint](#opera-utc-frame-selection)
7. [Cross-sensor comparison — precision-first framing (OPERA DIST vs EFFIS)](#cross-sensor-precision-first)
```

Note: §2 currently lacks a `<a name="pq-vs-ra"></a>` anchor (lines 133–135 don't have one). Add it. §4 currently lacks `<a name="dist-methodology"></a>` (line 367). Add both during TOC construction.

---

### `CHANGELOG.md` (append v1.1 entry)

**Analog:** self — existing `## [0.1.0] - 2026-04-09` entry (lines 7–99).

**Pattern** (lines 7–11):
```markdown
## [1.1.0] - 2026-04-28

### Added / Changed
...
```

**Content for v1.1 entry** (REL-04 deferral note per CONTEXT.md D-03):
- RTC:NAM matrix cell now renders as `DEFERRED` (N.Am. RTC not re-run in v1.1 EU-focus milestone; unblock: v1.2 N.Am. harness migration)
- `validation_methodology.md` §6 (OPERA UTC-hour frame selection) and §7 (cross-sensor precision-first framing) added
- TOC added to `validation_methodology.md`
- REL-04 TrueNAS Linux audit deferred to v1.2; infrastructure (Dockerfile, Apptainer.def, lockfiles) committed in v0.1.0

---

## Shared Patterns

### DEFERRED cell rendering (Phase 5 D-16; reused in Phase 7 D-01)

**Source:** `matrix_writer.py` lines 570–602 (`_render_dist_nam_deferred_cell`)
**Apply to:** new `_render_rtc_nam_deferred_cell`

```python
def _render_dist_nam_deferred_cell(metrics_path: Path) -> tuple[str, str] | None:
    import json as _json
    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.warning(
            "Failed to read deferred dist:nam metrics from {}: {}", metrics_path, e
        )
        return None
    cmr_outcome = raw.get("cmr_probe_outcome", "probe_failed")
    cell_status = raw.get("cell_status", "DEFERRED")
    pq_col = "—"
    ra_col = f"{cell_status} (CMR: {cmr_outcome})"
    return pq_col, ra_col
```

### Schema discriminator pattern

**Source:** `matrix_writer.py` lines 464–498 (`_is_dist_nam_shape`)
**Apply to:** new `_is_rtc_nam_deferred_shape`

Pattern: load raw JSON, check for presence of unique key(s), return bool. All discriminators use this exact template with a `try/except (OSError, ValueError)` guard and `logger.debug` on failure.

### CALIBRATING italics rendering

**Source:** `matrix_writer.py` lines 123–124 (`_render_cell_column`)
```python
return f"*{body}*" if any_calibrating else body
```

**Source:** `matrix_writer.py` line 346 (`_render_cslc_selfconsist_cell`)
```python
pq_col = f"*{pq_body}*{warn}"
```

**Source:** `matrix_writer.py` line 429 (`_render_disp_cell`)
```python
pq_col = f"*{pq_body} (CALIBRATING)*{warn}"
```

**Apply to:** Phase 7 appends `— binds v1.2` (or the DISP-specific variant) inside the `(CALIBRATING)` suffix in all three locations.

### Criterion registry read pattern

**Source:** `criteria.py` lines 28–47 (`Criterion` dataclass + `binding_after_milestone` field)
```python
@dataclass(frozen=True)
class Criterion:
    ...
    binding_after_milestone: str | None
    ...
```

Access in `matrix_writer.py`: `crit = CRITERIA.get(cid)` → `crit.binding_after_milestone`. Field is `str | None`; use `or "future milestone"` as fallback if None.

### Methodology section voice pattern

**Source:** `docs/validation_methodology.md` §1 (lines 17–130)

Structure for §6 and §7:
1. Section header: `## N. Title` + `<a name="anchor-id"></a>`
2. Bold TL;DR (one sentence)
3. Numbered sub-sections: `### N.1 Structural argument`, `### N.2 Policy statement`, `### N.3 Code pointer`, `### N.4 Diagnostic Evidence (Appendix)`
4. Policy statement uses "Do NOT / MUST / must not" language with explicit merge-gate rule
5. Code pointer cites function by qualified name + module path + line numbers

---

## No Analog Found

All 6 files have close analogs. No files require falling back to RESEARCH.md patterns.

---

## Metadata

**Analog search scope:** `src/subsideo/validation/`, `eval-dist/`, `eval-rtc-eu/`, `docs/`, repo root
**Files scanned:** `matrix_writer.py` (875 lines, full read), `criteria.py` (285 lines, full read), `matrix_manifest.yml` (99 lines), `eval-dist/metrics.json`, `eval-dist/meta.json`, `eval-rtc-eu/meta.json`, `docs/validation_methodology.md` (706 lines, 4 passes), `src/subsideo/validation/harness.py` (lines 1–60, 350–430), `src/subsideo/validation/effis.py` (lines 1–180), `results/matrix.md`, `CHANGELOG.md` (lines 1–99)
**Pattern extraction date:** 2026-04-28
