# Phase 6: DSWx-S2 N.Am. + EU Recalibration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-26
**Phase:** 06-dswx-s2-n-am-eu-recalibration
**Areas discussed:** EU fit-set AOI selection methodology; Grid search architecture & caching; Threshold module API shape (DSWX-05); Reporting framework + held-out Balaton + F1 ceiling citation; N.Am. positive control mechanics; Cross-cutting infra (CONCLUSIONS structure + methodology §5)

---

## EU fit-set AOI selection methodology

### Where do AOI candidates get committed?

| Option | Description | Selected |
|--------|-------------|----------|
| Probe artifact + plan-phase lock | Phase 2 D-04 / Phase 3 03-02 pattern; `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` + user lock-in checkpoint | ✓ |
| Notebook-only | FEATURES default; selection inline in notebook output | |
| Commit candidates in CONTEXT.md now | Skips the probe rigour; risks missing cloud-free / JRC-confidence checks | |

**User's choice:** Probe artifact + plan-phase lock.
**Notes:** De-risks 4-5 days of compute against AOI-quality cap (P5.2). Adds plan-phase 06-01 wave but matches Phase 2 + Phase 3 prior-decision pattern.

### Pre-screen automation level (P5.2 + P5.4 + OSM flags)?

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid auto + advisory | Hard-rejects on cloud-free unavailability, wet/dry < 1.2, JRC unknown > 20%; advisory on jrc_confidence + OSM tags | ✓ |
| Fully auto | Every check auto-rejects | |
| Advisory-only | Notebook flags everything; human decides everything | |

**User's choice:** Hybrid auto + advisory.
**Notes:** Matches Phase 2 D-13/D-14 'automation flags, doesn't replace narrative' discipline.

### P5.4 wet/dry water-extent ratio reject threshold?

| Option | Description | Selected |
|--------|-------------|----------|
| Strict 1.2 auto-reject | Per PITFALLS P5.4 explicit; alternate-year retry via JRC climatology lookup | ✓ |
| Lenient 1.1 + manual review | Lower threshold; risk of fitting threshold to data | |
| Score-only (no auto-reject) | Compute ratio as score; human decides | |

**User's choice:** Strict 1.2 auto-reject.

### Notebook deliverable structure?

| Option | Description | Selected |
|--------|-------------|----------|
| Two notebooks | `dswx_aoi_selection.ipynb` (research) + `dswx_recalibration.ipynb` (grid + LOO-CV viz) | ✓ |
| Single notebook | Combined research + viz | |
| Three notebooks | Add `dswx_fitset_construction.ipynb` middle | |

**User's choice:** Two notebooks. Per REQUIREMENTS DSWX-02 + DSWX-05 explicit.

---

## Grid search architecture & caching

### Caching strategy?

| Option | Description | Selected |
|--------|-------------|----------|
| Cache 5 intermediate index bands | MNDWI + NDVI + AWESH + MBSRV + MBSRN as float32 numpy `.npy`; ~30 GB total | ✓ |
| Cache 5-bit diagnostic per gridpoint | Massive storage (1 TB+); rejected | |
| Cache raw bands only | Status quo; ~20× slower | |
| Cache classified arrays per gridpoint subset | Premature optimisation | |

**User's choice:** Cache 5 intermediate index bands.
**Notes:** ~20× speedup. Decompose `_compute_diagnostic_tests` into public `compute_index_bands` + `score_water_class_from_indices`.

### Grid search parallelization?

| Option | Description | Selected |
|--------|-------------|----------|
| joblib processes per (AOI, scene) pair | Outer loop parallel; ~5-15 min wall on warm cache | ✓ |
| joblib threads on inner gridpoint loop | Thread overhead dominates; ignores macOS-fork hygiene | |
| Sequential | Simplest; ~12× slower | |
| MPI / dask cluster | Massive overkill | |

**User's choice:** joblib processes per (AOI, scene) pair.

### Restart-safe checkpoint shape?

| Option | Description | Selected |
|--------|-------------|----------|
| Per (AOI, scene) gridscores parquet/JSON-lines + final aggregate | Restart-safe at pair granularity; final results.json aggregate | ✓ |
| Single grid_results.json after-completion | No incremental progress; crash loses everything | |
| Per-gridpoint cache | 100k JSON files; filesystem-overhead dominates | |

**User's choice:** Per (AOI, scene) gridscores + final aggregate.

### Edge-of-grid sentinel?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-FAIL grid + force expansion | cell_status='BLOCKER' + exit non-zero on edge-best-point (P5.1 mitigation) | ✓ |
| Warn-only + log | Silent acceptance risk | |
| Auto-expand grid | Hard to bound runtime | |

**User's choice:** Auto-FAIL grid + force expansion.

---

## Threshold module API shape (DSWX-05)

### Type for `DSWEThresholds`?

| Option | Description | Selected |
|--------|-------------|----------|
| Frozen dataclass with slots=True | Matches Phase 1 D-09 `Criterion` pattern; provenance fields flow naturally | ✓ |
| NamedTuple | REQUIREMENTS phrasing; awkward for provenance + region selector | |
| Pydantic v2 BaseModel | Heavy for constants holder | |

**User's choice:** Frozen dataclass with slots=True.

### EU vs N.Am. region selector?

| Option | Description | Selected |
|--------|-------------|----------|
| Both: pydantic-settings env-var + DSWxConfig field | Env-var default + per-call override; matches REQUIREMENTS DSWX-05 explicit | ✓ |
| Pydantic-settings env-var only | Per-call override needs monkey-patch | |
| DSWxConfig field only | Conflicts with REQUIREMENTS pydantic-settings explicit | |

**User's choice:** Both: pydantic-settings env-var + DSWxConfig field.
**Notes:** `SUBSIDEO_DSWX_REGION: Literal['nam','eu'] = 'nam'` + `DSWxConfig.region: Literal['nam','eu'] | None = None`.

### Provenance metadata format?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline class attributes | Grep-discoverable; no I/O at import; immutable | ✓ |
| Sidecar JSON | Adds runtime I/O at import (rejected by REQUIREMENTS) | |
| Inline + sidecar copy in scripts/recalibrate_dswe_thresholds_results.json | Not exclusive — full grid heatmap data still in scripts JSON | |

**User's choice:** Inline class attributes.
**Notes:** `grid_search_run_date`, `fit_set_hash`, `fit_set_mean_f1`, `held_out_balaton_f1`, `loocv_mean_f1`, `loocv_gap`, `notebook_path`, `results_json_path` as dataclass fields. Full grid data lives in `scripts/recalibrate_dswe_thresholds_results.json` (referenced via `results_json_path`).

### v1.0 module-level constant disposition (`products/dswx.py:27-39`)?

| Option | Description | Selected |
|--------|-------------|----------|
| Replace inline + thread thresholds dict through run_dswx | Forces region-awareness via API surface; PSWT1_* stays | ✓ |
| Re-export from new module + back-compat alias | Hides region-awareness | |
| Mark deprecated + emit DeprecationWarning | Adds noise without value | |
| Stay-as-is (parallel constants) | Two sources of truth | |

**User's choice:** Replace inline + thread thresholds dict through run_dswx.
**Notes:** PSWT1_* (Test 4) and PSWT2_BLUE/NIR/SWIR1/SWIR2 stay at module level (not in recalibration grid). DELETE WIGT, AWGT, PSWT2_MNDWI from `products/dswx.py`.

---

## Reporting framework + held-out Balaton + F1 ceiling citation

### Officially reported EU matrix-cell F1?

| Option | Description | Selected |
|--------|-------------|----------|
| Held-out Balaton is THE matrix-cell value | BOOTSTRAP §5.4 + PITFALLS P5.1 explicit | ✓ |
| Fit-set mean is the matrix-cell value, Balaton is sanity check | Direct contradiction of P5.1 | |
| Both as separate cells | Departs from manifest 5×2 = 10-cell structure (REL-01) | |

**User's choice:** Held-out Balaton is THE matrix-cell value.
**Notes:** Fit-set mean F1 + LOO-CV mean F1 + per-AOI F1 breakdown reported alongside under `reference_agreement.diagnostics`.

### LOO-CV computation timing?

| Option | Description | Selected |
|--------|-------------|----------|
| Post-hoc on best gridpoint only | 12 LOO folds × 8400 gridpoints; ~5-15 min added | ✓ |
| During grid search per-gridpoint | 12× expensive; semantically wrong (over-fits to fit-set composition) | |
| Both: per-gridpoint + on-best | Defer to plan-phase if budget allows | |

**User's choice:** Post-hoc on best gridpoint only.

### Honest FAIL labelling for 0.85 ≤ F1 < 0.90?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse FAIL + named_upgrade_path field | Keeps cell_status Literal stable; structured side-channel | ✓ |
| Extend cell_status Literal with 'FAIL_WITH_UPGRADE_PATH' | Forces every dispatcher (Phases 1-5) to handle new state | |
| Inline annotation in CONCLUSIONS only | Hides milestone framing from canonical status artifact | |

**User's choice:** Reuse FAIL + named_upgrade_path field.

### Shoreline buffer (P5.2) + F1 ceiling citation (P5.3) policy?

| Option | Description | Selected |
|--------|-------------|----------|
| Buffer always-excluded + dual F1 reported + plan-phase PROTEUS probe | Single source of truth; transparent diagnostic; ceiling ground-referenced | ✓ |
| Buffer grid-search-only + ceiling delegated to §5 author | Fit/eval kernel mismatch | |
| No shoreline buffer + own-data ceiling claim | Ignores P5.2 commission/omission asymmetry + P5.3 telephone-game drift | |

**User's choice:** Buffer always-excluded + dual F1 reported + plan-phase PROTEUS probe.
**Notes:** `f1` (gate, shoreline-excluded) + `f1_full_pixels` (diagnostic). Plan-phase 06-01 fetches PROTEUS ATBD + locks §5.1 citation.

---

## N.Am. positive control mechanics

### Tahoe vs Pontchartrain decision mechanism?

| Option | Description | Selected |
|--------|-------------|----------|
| Runtime auto-pick by cloud-cover | CANDIDATES list + first-AOI-with-valid-scene wins | ✓ |
| Commit Tahoe upfront, Pontchartrain as fallback | Slightly less symmetrical | |
| Run BOTH and report higher F1 | Tunes matrix to easier AOI; rejected on principle | |
| Runtime user prompt | Defeats `make eval-all` reproducibility | |

**User's choice:** Runtime auto-pick by cloud-cover.

### Regression investigation flow when N.Am. F1 < 0.85 (DSWX-01)?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-flag in metrics.json + halt before EU recalibration | Phase 2 D-13/D-14 INVESTIGATION_TRIGGER pattern; assert in recalibration Stage 0 | ✓ |
| Auto-flag + warn but proceed to EU | Recalibration on broken pipeline risks misattribution | |
| Human-narrated only (no auto-flag) | Loses auditable trigger | |

**User's choice:** Auto-flag in metrics.json + halt before EU recalibration.

---

## Cross-cutting infra

### CONCLUSIONS file structure?

| Option | Description | Selected |
|--------|-------------|----------|
| Two CONCLUSIONS + v1.0 baseline preamble in EU file | NEW `CONCLUSIONS_DSWX_N_AM.md` + APPEND v1.1 sections to existing `CONCLUSIONS_DSWX.md` | ✓ |
| Two CONCLUSIONS + rename EU to CONCLUSIONS_DSWX_EU.md | Symmetrical with other products; needs git mv + manifest edit | |
| Single shared CONCLUSIONS_DSWX.md with two sections | Mismatches manifest | |

**User's choice:** Two CONCLUSIONS + v1.0 baseline preamble in EU file.

### `docs/validation_methodology.md` §5 sub-sections?

| Option | Description | Selected |
|--------|-------------|----------|
| 5 sub-sections | §5.1 ceiling citation + §5.2 Balaton vs fit-set + §5.3 shoreline buffer + §5.4 LOO-CV + §5.5 threshold module design | ✓ |
| 3 sub-sections (lean) | Couples LOO-CV (statistical) to held-out (methodological) | |
| 1 sub-section (minimal) | Departs from §3 + §4 multi-sub-section precedent | |

**User's choice:** 5 sub-sections.
**Notes:** §5 leads with structural argument (§5.1 ceiling) before empirical evidence (§5.2-§5.4) before design rationale (§5.5) per Phase 3 D-15 'kernel argument leads, diagnostic appendix follows'.

---

## Claude's Discretion

(Plan-phase 06-01 commits per CONTEXT.md `<decisions>` Claude's Discretion section)

- Per-(AOI, scene) gridscores serialisation format (parquet vs JSON-lines based on pyarrow availability)
- Specific MGRS tiles for Tahoe + Pontchartrain candidates
- `THRESHOLDS_NAM` provenance fields (PROTEUS-paper sentinel values)
- Regression-investigation auto-flag → `criteria.py` INVESTIGATION_TRIGGER entry decision
- `_compute_diagnostic_tests` decomposition specifics
- EXPECTED_WALL_S exact values (run_eval_dswx_nam.py = 1800 s estimate; recalibrate_dswe_thresholds.py = 21600 s estimate)
- §5.1 PROTEUS ATBD fetch path (Context7 vs WebFetch vs literature)
- `run_eval_dswx_nam.py` Stage layout (mirrors v1.0 9-stage with CANDIDATES outer loop)
- `scripts/recalibrate_dswe_thresholds.py` Stage layout (11 stages per CONTEXT.md)
- `docs/dswx_fitset_aoi_selection.md` rendering mechanism (auto vs hand-written)
- OSM / Copernicus Land Monitoring failure-mode tag query mechanism

---

## Deferred Ideas

(See CONTEXT.md `<deferred>` for full list)

- ML-replacement algorithm path (DSWX-V2-01)
- Global recalibration (DSWX-V2-02)
- Turbid-water / frozen-lake / mountain-shadow handling (DSWX-V2-03)
- Bootstrap CI on F1
- Per-AOI threshold tuning
- Interactive AOI picker UI (anti-feature)
- README PASS/FAIL badge (anti-feature)
- DSWx-S1 / DSWx-HLS new product classes
- `subsideo validate-dswx` CLI subcommand
- Burst-database-backed AOI catalogue query API
- `docs/validation_methodology.md` cross-section index (Phase 7 territory)
