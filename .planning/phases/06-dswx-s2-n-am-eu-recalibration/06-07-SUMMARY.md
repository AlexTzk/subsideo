---
phase: 06-dswx-s2-n-am-eu-recalibration
plan: 07
subsystem: validation
tags: [dswx, eu-rerun, balaton, conclusions-append, methodology-section-5, honest-fail]

requires:
  - phase: 06-06
    provides: honest BLOCKER closure; THRESHOLDS_EU unchanged (PROTEUS defaults); Stage 0 warning
  - phase: 06-05
    provides: N.Am. positive control F1=0.9252 PASS
  - phase: 06-04
    provides: compare_dswx single-return + .diagnostics attribute (B2 fix)
  - phase: 06-02
    provides: DswxEUCellMetrics schema + DSWEThresholdsRef + LOOCVPerFold + PerAOIF1Breakdown
  - phase: 06-01
    provides: PROTEUS ATBD probe Path (c) succeeded; F1_OSW=0.8786 OPERA Cal/Val

provides:
  - "EU DSWx re-run: Balaton F1=0.8165 (shoreline-excluded) FAIL -- fit-set quality review"
  - "eval-dswx/metrics.json + meta.json validated as DswxEUCellMetrics"
  - "CONCLUSIONS_DSWX.md v1.0 baseline preamble + 3 v1.1 sections appended"
  - "docs/validation_methodology.md §5 appended (5 sub-sections; Path (c) ceiling citation)"
  - "results/matrix.md regenerated -- dswx:eu F1=0.816 FAIL + dswx:nam F1=0.925 PASS"
  - "Phase 6 closed -- DSWx row complete in 5/5 product validation matrix"

affects:
  - results/matrix.md (dswx:eu cell now populated)
  - REQUIREMENTS.md (DSWX-06, DSWX-07 completion)

tech-stack:
  added: []
  patterns:
    - "Honest FAIL closure: F1<0.85 maps to named_upgrade_path='fit-set quality review'"
    - "Path (c) OPERA Cal/Val citation: OPERA-Cal-Val/DSWx-HLS-Requirement-Verification F1_OSW=0.8786"
    - "Stage 9 DswxEUCellMetrics write pattern: ProductQualityResultJson/ReferenceAgreementResultJson (not dataclasses)"
    - "gitignore: replace blanket eval-dswx/* with specific subdirectory excludes per eval-dswx_nam pattern"

key-files:
  created:
    - eval-dswx/metrics.json
    - eval-dswx/meta.json
    - .planning/phases/06-dswx-s2-n-am-eu-recalibration/06-07-SUMMARY.md
  modified:
    - run_eval_dswx.py
    - CONCLUSIONS_DSWX.md
    - docs/validation_methodology.md
    - results/matrix.md
    - .gitignore

key-decisions:
  - "EU re-run F1=0.8165 (shoreline-excluded) < 0.85 => named_upgrade_path='fit-set quality review' (not ML-replacement)"
  - "F1 full pixels=0.7957 (matches v1.0 baseline); shoreline exclusion adds +0.021 (confirmed JRC labelling noise)"
  - "ATBD probe Path (c) SUCCEEDED: OPERA Cal/Val F1_OSW=0.8786 mean across N=52 scenes; '0.92 ceiling' was misattribution"
  - "THRESHOLDS_EU = PROTEUS defaults under honest-BLOCKER closure; metrics.json thresholds_used.fit_set_hash='' documented"
  - "ProductQualityResultJson/ReferenceAgreementResultJson (from matrix_schema) used in DswxEUCellMetrics constructor, not the dataclasses from results.py (Rule 1 bug fix: Pydantic validation error)"
  - "eval-dswx/metrics.json + meta.json tracked via .gitignore exception (specific subdir excludes replace blanket eval-dswx/*)"

duration: 35min
completed: 2026-04-28
---

# Phase 6 Plan 07: EU DSWx Re-run + Reporting Summary

**EU DSWx Balaton re-run with PROTEUS defaults (recalibration deferred): F1=0.8165 FAIL -- named upgrade: fit-set quality review. Phase 6 closed.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-04-28T17:00:00Z
- **Completed:** 2026-04-28T17:35:00Z
- **Tasks:** 4
- **Files modified:** 6

## Accomplishments

### Task 1: EU DSWx re-run + metrics.json write

Modified `run_eval_dswx.py` with 5 changes per CONTEXT D-26 + iteration-1 fixes:
1. **Stage 0 W5**: `THRESHOLDS_EU.fit_set_hash` warning (pre-existing from Plan 06-06 relaxation; kept as-is per context notes)
2. **Stage 5**: `DSWxConfig(region="eu")` per D-10
3. **Stage 7**: single-return `validate = compare_dswx(...)` + `.diagnostics` attribute access (B2 fix; NOT tuple unpack)
4. **Stage 9 (new)**: `DswxEUCellMetrics` write to `eval-dswx/metrics.json` + `meta.json`; reads `scripts/recalibrate_dswe_thresholds_results.json` for fit_set/LOO-CV diagnostics
5. **Import cleanup**: removed unused harness imports; added `ProductQualityResultJson`, `ReferenceAgreementResultJson` from `matrix_schema`

**Execution results** (warm-path; SAFE + DSWx COG cached from Phase 6 v1.0 run):
- F1 (shoreline-excluded, gate) = **0.8165**
- F1 (full pixels, diagnostic) = 0.7957
- Precision = 0.9578 | Recall = 0.7115 | Accuracy = 0.9866
- Shoreline buffer excluded = 187,556 pixels
- cell_status = **FAIL** | named_upgrade_path = **'fit-set quality review'** (F1 < 0.85)
- loocv_gap = NaN (recalibration deferred; vacuously met)
- THRESHOLDS_EU = PROTEUS defaults (WIGT=0.124, AWGT=0.0, PSWT2_MNDWI=-0.5)

**Rule 1 bug fixed (deviation):** `DswxEUCellMetrics` constructor requires `ProductQualityResultJson` / `ReferenceAgreementResultJson` (Pydantic BaseModel from `matrix_schema`), not the dataclass `ProductQualityResult` / `ReferenceAgreementResult` from `results.py`. Pydantic v2 validation error caught and fixed by switching to the correct types.

### Task 2: CONCLUSIONS_DSWX.md v1.1 append (D-21 pattern)

- Wrapped existing v1.0 content under `## v1.0 Balaton baseline (PROTEUS DSWE defaults; F1=0.7957 against JRC)`
- Appended 3 v1.1 sections:
  - `## v1.1 Recalibrated thresholds (region=eu)`: Honest BLOCKER framing; 3-iteration grid search exhausted; PROTEUS defaults retained; HLS→S2 L2A cross-sensor gap root cause; v1.2 recommendations
  - `## v1.1 Held-out Balaton F1 + LOO-CV gap`: Full metrics table (F1=0.8165 gate, 0.7957 full, 187556 excluded, NaN LOO-CV); interpretation of shoreline exclusion effect (+0.021)
  - `## v1.1 Matrix-cell verdict + named upgrade path`: F1=0.8165 FAIL; named_upgrade_path='fit-set quality review'; honest FAIL framing; no goalpost-move; cross-reference to CONCLUSIONS_DSWX_EU_RECALIB.md

### Task 3: docs/validation_methodology.md §5 append (D-22)

Appended `## 5. DSWE F1 ceiling, held-out Balaton, and threshold-module design` with 5 sub-sections:
- §5.1: Path (c) SUCCEEDED. OPERA Cal/Val F1_OSW=0.8786 mean (N=52 scenes). "0.92 ceiling" was OSW class accuracy misattributed as F1. Gate at 0.90 is above the Cal/Val baseline (project ambition, not literature claim).
- §5.2: BOOTSTRAP §5.4 + PITFALLS P5.1 held-out methodology. Phase 6 outcome: BLOCKER + F1=0.8165.
- §5.3 (W4 fix): Pekel et al. 2016 Nature 540:418–422 + PITFALLS §P5.2 commission/omission bounds. Phase 6 evidence: 187,556 px excluded, +0.021 F1 gain.
- §5.4: DSWX-06 LOO-CV gap < 0.02 gate. B1 10-fold leave-one-pair-out. Phase 6: NaN (vacuously met; recalib deferred).
- §5.5: DSWEThresholds frozen+slots dataclass; THRESHOLDS_NAM + THRESHOLDS_EU singletons; region selector precedence; W5 warning behavior.
- ZERO edits to existing §1-§4 (confirmed via `git diff | grep -E '^-## [1-4]\.'` = 0).

### Task 4: results/matrix.md regenerated

- `dswx:eu`: F1=0.816 FAIL — named upgrade: fit-set quality review | LOOCV gap=nan
- `dswx:nam`: F1=0.925 PASS [aoi=Lake Tahoe (CA)]
- All 10 cells present in matrix

## Task Commits

1. **Task 1** - `1a8ceba` (feat(06-07): EU DSWx re-run -- Balaton F1=0.8165 FAIL + DswxEUCellMetrics write)
2. **Task 2** - `b61fa3d` (docs(06-07): append v1.1 sections to CONCLUSIONS_DSWX.md)
3. **Task 3** - `ad56005` (docs(06-07): append §5 to validation_methodology.md)
4. **Task 4** - `651fd48` (chore(06-07): regenerate results/matrix.md -- dswx:eu F1=0.816 FAIL)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pydantic type mismatch in DswxEUCellMetrics constructor**
- **Found during:** Task 1 Stage 9 execution
- **Issue:** `DswxEUCellMetrics` expects `ProductQualityResultJson` / `ReferenceAgreementResultJson` (Pydantic BaseModel from `matrix_schema`), but the Stage 9 code used `ProductQualityResult` / `ReferenceAgreementResult` (Python dataclasses from `results.py`). Pydantic v2 raises `ValidationError: Input should be a valid dictionary or instance of ProductQualityResultJson`.
- **Fix:** Switched to import `ProductQualityResultJson` and `ReferenceAgreementResultJson` from `subsideo.validation.matrix_schema`; used these in the `DswxEUCellMetrics(...)` constructor.
- **Files modified:** `run_eval_dswx.py`
- **Commit:** `1a8ceba`

**2. [Rule 2 - Auto-add] .gitignore: eval-dswx/* was blanket-ignored**
- **Found during:** Task 1 commit attempt
- **Issue:** `eval-dswx/*` gitignored all files including metrics.json and meta.json, which must be tracked per the plan (and per the eval-dswx_nam pattern where only input/, output/, jrc/, stac_*.json are excluded).
- **Fix:** Replaced blanket `eval-dswx/*` with specific subdirectory excludes: `eval-dswx/input/`, `eval-dswx/output/`, `eval-dswx/jrc_cache/`, `eval-dswx/stac_items.json`, `eval-dswx/run.log`.
- **Files modified:** `.gitignore`
- **Commit:** `1a8ceba`

**3. [Rule 1 - Bug] Plan interfaces showed example results.json with PASS/loocv_per_fold (hypothetical)**
- **Found during:** Task 1 Stage 9 implementation
- **Issue:** The plan's `<interfaces>` section showed `recalibrate_dswe_thresholds_results.json` with hypothetical PASS data (`"cell_status": "PASS"`, `"loocv_per_fold": [...]`, etc.). The actual file from Plan 06-06 is a BLOCKER file with `"cell_status": "BLOCKER"`, no `loocv_per_fold`, no `per_aoi_breakdown`, NaN for LOO-CV fields. Stage 9 code correctly uses `.get("loocv_per_fold", [])` defensively.
- **Fix:** No code change needed; the defensive `.get()` pattern already handled the missing keys. Documented in Stage 9 comments.
- **Files modified:** None (design deviation, not code)

## Known Stubs

- `THRESHOLDS_EU.fit_set_hash = ""` — intentional under honest-BLOCKER closure; documented in CONCLUSIONS_DSWX_EU_RECALIB.md and run_eval_dswx.py Stage 0 warning. Resolved in v1.2 when EU recalibration lands.
- `THRESHOLDS_EU.grid_search_run_date = "2026-MM-DD"` — PLACEHOLDER; never overwritten by Plan 06-06 (honest-BLOCKER). Documented in metrics.json thresholds_used provenance stamp. Does NOT block plan's goal: the Balaton F1 is computed correctly against PROTEUS defaults and the cell_status=FAIL is properly reported.
- `loocv_gap = NaN` — expected under BLOCKER closure (no recalibration landed). Documented in all output artifacts.

## Phase 6 Close

Phase 6 is now complete. The DSWx row is populated in the 5/5 product validation matrix:
- `dswx:nam`: F1=0.9252 PASS (Lake Tahoe, Plan 06-05)
- `dswx:eu`: F1=0.8165 FAIL — named upgrade: fit-set quality review (Plan 06-07)

The EU recalibration investigation produced an honest BLOCKER diagnosis (HLS→S2 L2A spectral
transfer gap) documented in CONCLUSIONS_DSWX_EU_RECALIB.md. v1.2 requirements:
labeled S2 L2A training data + scene-level cross-calibration function.

---

## Self-Check: PASSED

Created files:
- `eval-dswx/metrics.json` — FOUND ✓
- `eval-dswx/meta.json` — FOUND ✓
- `.planning/phases/06-dswx-s2-n-am-eu-recalibration/06-07-SUMMARY.md` — FOUND ✓

Commits:
- `1a8ceba` — FOUND ✓
- `b61fa3d` — FOUND ✓
- `ad56005` — FOUND ✓
- `651fd48` — FOUND ✓
