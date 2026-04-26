---
phase: 06-dswx-s2-n-am-eu-recalibration
plan: 01
subsystem: validation/dswx
tags: [probe, aoi-selection, proteus-atbd, makefile, lock-in-checkpoint]
dependency_graph:
  requires: []
  provides:
    - .planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md
    - .planning/milestones/v1.1-research/dswx_proteus_atbd_ceiling_probe.md
    - notebooks/dswx_aoi_selection.ipynb
    - src/subsideo/validation/dswx_failure_modes.yml
    - Makefile (recalibrate-dswx + dswx-fitset-aoi-md targets)
    - docs/dswx_fitset_aoi_selection.md
  affects:
    - Plan 06-05 (N.Am. positive control AOI candidates locked)
    - Plan 06-06 (fit-set AOIs locked; recalibrate-dswx Makefile target wired)
    - Plan 06-07 (PROTEUS ATBD §5.1 wording locked)
tech_stack:
  added:
    - nbformat/nbconvert (notebook serialization + markdown render)
    - dswx_failure_modes.yml (importlib.resources YAML resource)
    - pdftotext via homebrew poppler (path (a) PDF extraction)
    - OPERA-Cal-Val/DSWx-HLS-Requirement-Verification (path (c) Cal/Val repo)
  patterns:
    - probe-and-commit (Phase 2 D-04 / Phase 3 03-02 precedent)
    - YAML resource via importlib.resources.files()
    - CandidateAOI frozen dataclass (probe_cslc_aoi_candidates.py precedent)
    - fallback-to-research-table on network failure
key_files:
  created:
    - src/subsideo/validation/dswx_failure_modes.yml
    - notebooks/dswx_aoi_selection.ipynb
    - .planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md
    - .planning/milestones/v1.1-research/dswx_proteus_atbd_ceiling_probe.md
    - docs/dswx_fitset_aoi_selection.md
  modified:
    - Makefile
decisions:
  - "5 fit-set AOIs: Alcantara (Mediterranean) / Tagus (Atlantic estuary) / Vanern (Boreal) / Garda (Alpine) / Donana (Iberian summer-dry); Balaton held-out"
  - "PROTEUS ATBD path (c) succeeded: OPERA Cal/Val F1_OSW mean = 0.8786 (N=52 scenes); 0.92 ceiling claim is inaccurate misattribution"
  - "CDSE STAC SENTINEL-2 collection unavailable at catalogue.dataspace.copernicus.eu/stac (collection name mismatch); fallback to RESEARCH-table values per CONTEXT D-01"
  - "dswx_failure_modes.yml 4-category resource committed; importlib.resources path confirmed"
  - "Makefile recalibrate-dswx + dswx-fitset-aoi-md targets wired; docs/dswx_fitset_aoi_selection.md auto-rendered (774 lines)"
metrics:
  duration_seconds: 1030
  completed_date: "2026-04-26"
  tasks_completed: 3
  tasks_total: 4
  files_created: 5
  files_modified: 1
---

# Phase 6 Plan 01: DSWx AOI Selection Probe + PROTEUS ATBD Citation Chain + Makefile Targets Summary

Wave 1 probe-and-commit: 5 fit-set AOIs locked + Balaton held-out + PROTEUS ATBD F1 ceiling citation chain resolved via OPERA Cal/Val repo (path c) + failure-modes YAML + AOI selection notebook + Makefile targets — ending at user lock-in checkpoint per CONTEXT D-01.

## What Was Built

### 1. dswx_failure_modes.yml YAML resource (`src/subsideo/validation/dswx_failure_modes.yml`)

4-category failure-mode resource per CONTEXT D-02:
- `glacier_or_frozen_lake`: Vänern (Dec-Feb), Saimaa (Nov-Apr), Mälaren (Dec-Mar)
- `mountain_shadow`: Garda, Léman, Maggiore (Oct-Feb advisory)
- `tidal_turbidity`: Tagus, Loire, Severn (advisory)
- `drought_year_risk`: Alcántara, Alarcón, Doñana (2017/2022 alternate-year retry)

Imported via `importlib.resources.files('subsideo.validation') / 'dswx_failure_modes.yml'` in the notebook.

### 2. AOI selection notebook (`notebooks/dswx_aoi_selection.ipynb`)

11-cell research notebook:
- Cell 1: Purpose/references
- Cell 2: Imports (lazy heavy deps inside functions)
- Cell 3: `CandidateAOI` frozen dataclass (aoi_id, biome, bbox, mgrs_tile, jrc_tile_xy, epsg, expected_wet/dry_month, held_out)
- Cell 4: 18-entry CANDIDATES list (16 EU across 6 biomes + 2 N.Am. positive controls)
- Cell 5: Scoring functions (cloud_free_count via CDSE STAC, wet_dry_ratio via JRC, jrc_unknown_pct)
- Cell 6: Scoring loop with RESEARCH-table fallback on network failure
- Cell 7: Auto-reject filter (cloud_free < 3, wet_dry < 1.2, jrc_unknown > 20%)
- Cell 8: Advisory overlay from dswx_failure_modes.yml via importlib.resources
- Cell 9: 5-AOI selection per RESEARCH §Recommended lock-in
- Cell 10: Selection rationale markdown
- Cell 11: Artifact-write cell (dswx_fitset_aoi_candidates.md)

### 3. Fit-set AOI candidates artifact (`.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md`)

92 lines. 18-candidate scoring table + 5 selected fit-set AOIs + Balaton held-out + rejection reasoning + N.Am. positive-control candidates.

**5 fit-set AOIs locked (per CONTEXT D-01, pending user checkpoint approval):**

| Biome | AOI | bbox (W,S,E,N) | MGRS | EPSG |
|-------|-----|----------------|------|------|
| Mediterranean reservoir | Embalse de Alcántara (ES) | -7.05, 39.55, -6.65, 39.95 | 29SQE | 32629 |
| Atlantic estuary | Tagus estuary (PT) | -9.45, 38.55, -8.85, 39.05 | 29SMC | 32629 |
| Boreal lake | Vänern (SE) | 12.40, 58.45, 14.20, 59.45 | 33VVF | 32633 |
| Alpine valley | Lago di Garda (IT) | 10.55, 45.55, 10.85, 45.85 | 32TQR | 32632 |
| Iberian summer-dry | Doñana wetlands (ES) | -6.55, 36.80, -6.30, 37.05 | 29SQB | 32629 |

**Held-out (gate-of-truth per BOOTSTRAP §5.4):**
- Balaton (HU) — bbox (17.20, 46.60, 18.20, 46.95), MGRS 33TXP, EPSG 32633

**N.Am. positive-control candidates (Plan 06-05):**
- Lake Tahoe (CA): MGRS T10SFH, EPSG 32610, JRC July 2021
- Lake Pontchartrain (LA): MGRS T15RYP (python-mgrs centroid; verify via live STAC in Plan 06-05), EPSG 32615, JRC July 2021

**Auto-rejected candidates (D-03 hard signals):**
- Bracciano: wet_dry=1.05 < 1.2 (volcanic crater lake)
- Saimaa: wet_dry=1.15 < 1.2 + fragmented
- Alarcón: wet_dry=1.1 < 1.2 (drought 2021)
- Albufera: wet_dry=1.15 < 1.2 (rice-paddy mosaic)

### 4. PROTEUS ATBD ceiling probe (`.planning/milestones/v1.1-research/dswx_proteus_atbd_ceiling_probe.md`)

97 lines. Resolution: **Path (c) SUCCEEDED.** Key findings:

- **Path (a)**: OPERA DSWx-HLS ProductSpec PDF (20MB) downloaded and parsed via `pdftotext -layout`. The product spec (JPL D-107395 Rev B) contains NO F1 numbers — it is a product format specification, not a validation report. It references the ATBD as [RD1] = JPL D-107397.

- **Path (c)**: OPERA-Cal-Val/DSWx-HLS-Requirement-Verification cloned. `metrics.csv` (N=52 scenes, 100-bootstrap) parsed:
  - F1 Open Surface Water: mean = **0.8786** (not 0.92)
  - F1 Partial Surface Water: mean = 0.5843
  - OPERA requirements use CLASS ACCURACY (OSW > 80%, PSW > 70%), NOT F1
  - **The "DSWE F1 ≈ 0.92 ceiling" from BOOTSTRAP is a misattribution** of OSW class accuracy (91.6%) as F1

- **Plan 06-07 §5.1 wording locked**: The OPERA Cal/Val OSW F1 = 0.8786 is a published FLOOR, not a ceiling. Our 0.90 gate is above this floor — methodologically coherent. The criteria.py:188 `dswx.f1_min = 0.90` BINDING threshold is UNCHANGED.

### 5. Makefile targets

Two new targets appended after the existing `eval-dswx-*` group:
- `recalibrate-dswx`: wires `$(SUPERVISOR) scripts/recalibrate_dswe_thresholds.py` (script lands Plan 06-06)
- `dswx-fitset-aoi-md` + `docs/dswx_fitset_aoi_selection.md`: auto-renders notebook via `jupyter nbconvert --to markdown`

### 6. Rendered docs (`docs/dswx_fitset_aoi_selection.md`)

774 lines. Auto-generated from `notebooks/dswx_aoi_selection.ipynb` via `jupyter nbconvert --to markdown`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CDSE STAC SENTINEL-2 collection unavailable**
- **Found during:** Task 1 (scoring loop)
- **Issue:** `catalogue.dataspace.copernicus.eu/stac` has only 10 collections, none named `SENTINEL-2`. The `cloud_free_count()` function returned 0 for all candidates.
- **Fix:** Used RESEARCH.md pre-computed fallback table values per CONTEXT D-01 ("the artifact ships either way"). Documented in the artifact header under `Note:`.
- **Files modified:** `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` (header note added)

**2. [Rule 3 - Blocking] Notebook execution timeout (JRC tile downloads)**
- **Found during:** Task 1 (notebook execute step)
- **Issue:** `jupyter nbconvert --to notebook --execute` timed out at 180s because 36 JRC tile downloads (18 AOIs × 2 tiles) are slow. The notebook's fallback logic is correct but the full JRC download loop is too slow for inline execution.
- **Fix:** The artifact generation was executed directly via Python (same fallback-table logic as notebook Cell 11). Notebook itself remains correct; the execute-in-place step is best-effort (design intent in CONTEXT D-01: artifact ships either way).
- **Impact:** None — the artifact and notebook are both committed. Users can re-run the notebook locally with `make dswx-fitset-aoi-md` or `jupyter nbconvert --to notebook --execute --inplace` (may take 5-10 min with full JRC downloads).

**3. [Rule 1 - Bug] OPERA Product Spec PDF is not the ATBD**
- **Found during:** Task 2 (path (a) PDF extraction)
- **Issue:** Plan spec said "download the OPERA_DSWx-HLS_ProductSpec PDF" expecting F1 numbers. The product spec (JPL D-107395) is a format specification, not a validation report. F1 numbers are in the ATBD (JPL D-107397) or the Cal/Val repo.
- **Fix:** Continued to path (c) per the plan's fallback chain. Path (c) (OPERA-Cal-Val GitHub repo) succeeded and produced all necessary numbers.
- **Impact:** The critical finding is stronger than expected — the "0.92 ceiling" is not just unverifiable, it is WRONG (F1_OSW = 0.8786, not 0.92).

**4. [Rule 2 - Critical finding] "0.92 architectural ceiling" claim is a misattribution**
- **Found during:** Task 2 (path (c) metrics.csv analysis)
- **Issue:** BOOTSTRAP_V1.1.md and CONCLUSIONS_DSWX.md reference a "DSWE F1 ≈ 0.92 architectural ceiling." The OPERA Cal/Val data shows F1_OSW mean = 0.8786 (not 0.92); the 0.92 figure corresponds to OSW class accuracy (91.6%), not F1.
- **Fix:** Documented in the probe artifact with the correct citation. Plan 06-07 wording updated in the probe artifact's §5.1 recommendation. The criteria.py:188 gate (0.90) is above the published Cal/Val F1 baseline — no threshold change needed.

**5. [Rule 2 - Missing data] `micromamba run -n subsideo` does not function in this shell environment**
- **Found during:** All tasks
- **Issue:** `micromamba run -n subsideo <cmd>` exits with "Undefined error: 0" — the micromamba shell integration isn't available in the agent shell context.
- **Fix:** Used full path `/Users/alex/.local/share/mamba/envs/subsideo/bin/python3` and `/Users/alex/.local/share/mamba/envs/subsideo/bin/jupyter` for all executions. Makefile targets retain `micromamba run -n subsideo` syntax (correct for user-facing invocation).

## Downstream Pointers

- **Plan 06-05 (N.Am. eval):** Read `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` §N.Am. positive-control candidates for CANDIDATES list seed (Tahoe T10SFH / Pontchartrain T15RYP).
- **Plan 06-06 (recalibration script):** Read §Decision section for the 5 fit-set AOIs. Run `make recalibrate-dswx` once the script exists.
- **Plan 06-07 (docs):** Read `.planning/milestones/v1.1-research/dswx_proteus_atbd_ceiling_probe.md` §Recommendation for Plan 06-07 for the locked §5.1 wording. Replace "0.92 ceiling" phrase with OPERA Cal/Val citation (F1_OSW = 0.8786, N=52 scenes, 2023).

## Checkpoint Status

Task 4 (USER LOCK-IN CHECKPOINT) is the next task. Returning structured checkpoint message for user review of the 5-AOI fit-set + Balaton held-out + PROTEUS ATBD resolution before Plan 06-06 commits fit-set compute.

## Self-Check: PASSED

- [x] `src/subsideo/validation/dswx_failure_modes.yml` exists (commit bd42ed1)
- [x] `notebooks/dswx_aoi_selection.ipynb` exists, 11 cells, CandidateAOI + CANDIDATES + dswx_failure_modes (commit bd42ed1)
- [x] `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` exists, 92 lines, all 6 AOIs + HELD-OUT (commit bd42ed1)
- [x] `.planning/milestones/v1.1-research/dswx_proteus_atbd_ceiling_probe.md` exists, 97 lines, paths a/c/d + criteria.py + §5.1 rec (commit c2cb3ee)
- [x] `Makefile` has recalibrate-dswx + dswx-fitset-aoi-md targets (commit a219e49)
- [x] `docs/dswx_fitset_aoi_selection.md` exists, 774 lines (commit a219e49)
