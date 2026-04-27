---
phase: 06-dswx-s2-n-am-eu-recalibration
plan: 05
subsystem: validation
tags: [n-am-positive-control, dswx-s2, jrc, candidates-iteration, investigation-trigger, conclusions, checkpoint]
dependency_graph:
  requires: [06-01, 06-02, 06-03, 06-04]
  provides: [eval-dswx_nam/metrics.json, eval-dswx_nam/meta.json, CONCLUSIONS_DSWX_N_AM.md, run_eval_dswx_nam.py]
  affects: [06-06 Stage 0 gate reads eval-dswx_nam/metrics.json]
tech_stack:
  added: []
  patterns:
    - CANDIDATES declarative list + cloud-cover first-winner iteration (D-18)
    - DSWxConfig(region='nam') THRESHOLDS_NAM threading (Plan 06-03)
    - W2 fix: f1_full_pixels + shoreline_buffer_excluded_pixels inline in DswxNamCellMetrics (no sidecar)
    - B2 fix: validation = compare_dswx(...) + diagnostics via .diagnostics attribute
    - INVESTIGATION_TRIGGER F1 < 0.85 gate (CONTEXT D-20)
    - Rule 3 fix: gdal_JP2OpenJPEG.dylib plugin manually copied from conda pkg cache
key_files:
  created:
    - run_eval_dswx_nam.py
    - tests/unit/test_run_eval_dswx_nam_smoke.py
    - eval-dswx_nam/metrics.json
    - eval-dswx_nam/meta.json
    - CONCLUSIONS_DSWX_N_AM.md
  modified:
    - src/subsideo/validation/_mgrs_tiles.geojson
    - .gitignore
    - results/matrix.md
decisions:
  - "F1=0.9252 (shoreline-excluded) > 0.90 BINDING PASS at Lake Tahoe T10SFH July 2021"
  - "THRESHOLDS_NAM PROTEUS defaults (WIGT=0.124, AWGT=0.0, PSWT2_MNDWI=-0.5) operate at calibration baseline"
  - "f1_below_regression_threshold=False: EU recalibration (Plan 06-06) cleared to proceed"
  - "JP2OpenJPEG GDAL plugin was missing from subsideo env; fixed by copying from conda pkg cache"
  - "MGRS seed tiles 10SFH + 15RYP added with pyproj-computed WGS84 bounds"
metrics:
  duration: "~45 min (including JP2 plugin fix + re-run)"
  completed_date: "2026-04-27"
  tasks_completed: 3
  tasks_total: 4
  files_modified: 8
---

# Phase 06 Plan 05: N.Am. DSWx-S2 Positive Control Summary

**One-liner:** N.Am. DSWx-S2 eval F1=0.9252 PASS (Lake Tahoe T10SFH July 2021; THRESHOLDS_NAM PROTEUS defaults; EU recalibration cleared; W2+B2+JP2 fixes integrated).

## What Was Built

### Task 1: run_eval_dswx_nam.py (committed 69fa2df — prior agent)

10-stage CANDIDATES harness with:
- `CANDIDATES: list[AOIConfig]` = [Lake Tahoe 10SFH (primary), Lake Pontchartrain 15RYP (fallback)]
- `EXPECTED_WALL_S = 1800`; supervisor watchdog 2× = 3600s
- Stage 2: STAC cloud-cover first-winner iteration (D-18)
- Stage 5: `run_dswx(DSWxConfig(..., region='nam'))` → THRESHOLDS_NAM applied (Plan 06-03)
- Stage 7: `validation = compare_dswx(...)` + `diagnostics = validation.diagnostics` (B2 fix)
- Stage 8: INVESTIGATION_TRIGGER (F1 < 0.85 → 3 regression audits required)
- Stage 9: `DswxNamCellMetrics` write with W2 fix (f1_full_pixels + shoreline_buffer_excluded_pixels inline)
- Static smoke tests: 12 invariants covering EXPECTED_WALL_S, CANDIDATES shape, B2 attribute access, W2 no-sidecar

### Task 2: Execute eval-dswx-nam

**Results:**
- **Selected AOI:** Lake Tahoe (CA), MGRS 10SFH, EPSG 32610
- **Scene:** S2B_MSIL2A_20210723T184919_N0500_R113_T10SFH_20230131T130926 (cloud cover 0.0%)
- **F1 = 0.9252** (shoreline-excluded; > 0.90 BINDING) → **PASS**
- **Precision = 0.8999**, **Recall = 0.9521**, **Accuracy = 0.9973**
- **f1_full_pixels = 0.8613** (W2 fix: inline in metrics.json)
- **shoreline_buffer_excluded_pixels = 243,221** (W2 fix: inline in metrics.json)
- **cell_status = PASS**, **named_upgrade_path = None**
- **f1_below_regression_threshold = False** → Plan 06-06 gate passes automatically
- **wall_s = 14s** (warm path; SAFE cached; 1786s headroom under 1800s budget)

### Task 3: CONCLUSIONS_DSWX_N_AM.md (committed 0faeb32)

159-line document with all 5 sections per CONTEXT D-21(a):
1. Objective — positive control framing + pass criteria table
2. Test Setup — selected AOI, candidates attempted, scene metadata
3. Pipeline Run — wall time table, threshold module applied, BOA offsets, output histogram
4. Reference-Agreement — F1 table with BINDING criterion; W2 fix note (no sidecar)
5. Investigation Findings — "Not triggered (F1=0.9252 >= 0.85)"

### Task 4: USER CHECKPOINT (pending — plan stops here)

The plan specifies a `checkpoint:human-verify` gate before Plan 06-06 fit-set compute proceeds.

## Eval Output Files

| File | Status | Content |
|------|--------|---------|
| `eval-dswx_nam/metrics.json` | committed 67427e4 | F1=0.9252, cell_status=PASS, W2 fields inline |
| `eval-dswx_nam/meta.json` | committed 67427e4 | git_sha, selected_aoi, input_hashes |
| `results/matrix.md` | committed b86d8ea | DSWX NAM row: "F1=0.925 PASS [aoi=Lake Tahoe (CA)]" |
| `CONCLUSIONS_DSWX_N_AM.md` | committed 0faeb32 | 159 lines, 5 sections, actual F1 values |

NO `eval-dswx_nam/diagnostics.json` sidecar (W2 fix: fields in metrics.json).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] MGRS tiles 10SFH + 15RYP missing from seed file**

- **Found during:** Task 2 execution attempt (previous agent)
- **Issue:** `bounds_for_mgrs_tile('10SFH')` raised `ValueError`; seed file only covered EU tiles (10TFK, 29TNF, 33TXP) and one N.Am. tile (10TFK for dist, not dswx)
- **Fix:** Used pyproj to compute precise WGS84 bounds from UTM zone 10N/15N, then added both tiles to `src/subsideo/validation/_mgrs_tiles.geojson`
  - 10SFH: `(-121.8477, 38.8431, -120.6664, 39.7264)`
  - 15RYP: `(-90.9304, 29.7940, -89.8682, 30.6951)`
- **Files modified:** `src/subsideo/validation/_mgrs_tiles.geojson`
- **Commit:** `ef03edf`

**2. [Rule 3 - Blocking] GDAL JP2OpenJPEG plugin missing from subsideo conda env**

- **Found during:** Task 2 Stage 5 (DSWx pipeline run_dswx)
- **Issue:** `gdal_JP2OpenJPEG.dylib` not installed in subsideo conda environment; Sentinel-2 L2A `.jp2` band files unreadable; `rasterio.open()` raised "not recognized as being in a supported file format"
- **Fix:** Located `libgdal-jp2openjpeg-3.12.3` in conda pkg cache (`~/.local/share/mamba/pkgs/`); copied `gdal_JP2OpenJPEG.dylib` to env's `lib/gdalplugins/`; verified `JP2OpenJPEG` driver now in `gdal.GetDriverCount()` listing
- **Note:** `micromamba install` failed with "Invalid argument" from pip-inspect subprocess bug in micromamba 2.5.0; manual copy was the correct workaround
- **Files modified:** `~/.local/share/mamba/envs/subsideo/lib/gdalplugins/gdal_JP2OpenJPEG.dylib` (outside git repo)
- **Commit:** N/A (environment-level fix)

**3. [Rule 2 - Missing] eval-dswx_nam large dirs not gitignored**

- **Found during:** Task 2 post-commit check
- **Issue:** `eval-dswx_nam/input/` (SAFE ~1.5GB), `output/`, `jrc/`, `stac_*.json` cache were untracked
- **Fix:** Added patterns to `.gitignore`; metrics.json and meta.json remain tracked
- **Files modified:** `.gitignore`
- **Commit:** `afab7b6`

## Threat Model Verification

| Threat | Status |
|--------|--------|
| T-06-05-01: Spoofing (scene selection) | meta.json records git SHA + input hashes (ef03edf source; safe_filename_hash_prefix=eb6332373ae556d0; threshold_module=f185156eae80ff08) |
| T-06-05-02: Tampering (INVESTIGATION_TRIGGER gate) | f1_below_regression_threshold=False in committed metrics.json; investigation_resolved=False (not needed since F1>0.90) |
| T-06-05-04: DoS (both candidates fail) | Not triggered; Tahoe selected at Stage 2 |
| T-06-05-05: Repudiation (F1 drift) | meta.json + git_sha=ef03edfc168e9d6cd4e1b18611d1eedb08726550 fix the measurement |
| T-06-05-06: Tampering (regression_diagnostic_required) | Hardcoded list `['boa_offset_check', 'claverie_xcal_check', 'scl_mask_audit']` — not user-supplied |

## Plan 06-06 Gate Status

Plan 06-06 Stage 0 reads `eval-dswx_nam/metrics.json` and asserts:
```python
not f1_below_regression_threshold OR investigation_resolved
```

Current state:
- `regression.f1_below_regression_threshold = False`
- Gate: `not False OR False` = `True` → **GATE PASSES**

EU recalibration fit-set compute (Plan 06-06) is cleared to proceed once the user approves this checkpoint.

## Self-Check

**Checking created files exist:**
- `run_eval_dswx_nam.py`: EXISTS (committed 69fa2df)
- `eval-dswx_nam/metrics.json`: EXISTS (committed 67427e4)
- `eval-dswx_nam/meta.json`: EXISTS (committed 67427e4)
- `CONCLUSIONS_DSWX_N_AM.md`: EXISTS (committed 0faeb32)
- `src/subsideo/validation/_mgrs_tiles.geojson`: MODIFIED (committed ef03edf)

**Checking commits exist:**
- `ef03edf`: fix(06-05): add N.Am. MGRS tiles 10SFH + 15RYP
- `67427e4`: feat(06-05): run N.Am. DSWx eval F1=0.9252 PASS
- `b86d8ea`: chore(06-05): regenerate matrix.md
- `0faeb32`: docs(06-05): add CONCLUSIONS_DSWX_N_AM.md
- `afab7b6`: chore(06-05): gitignore eval-dswx_nam large-file subdirs

**Schema validation:**
- `DswxNamCellMetrics.model_validate_json(metrics.json)`: PASSED
- `_is_dswx_nam_shape(metrics.json)`: True
- `_render_dswx_nam_cell(metrics.json)`: `('—', 'F1=0.925 PASS [aoi=Lake Tahoe (CA)]')`

## Self-Check: PASSED
