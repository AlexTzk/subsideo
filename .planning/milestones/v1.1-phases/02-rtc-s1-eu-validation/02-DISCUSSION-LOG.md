# Phase 2: RTC-S1 EU Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 02-rtc-s1-eu-validation
**Areas discussed:** Burst selection & probe, Script orchestration, metrics.json shape, Investigation trigger

---

## Burst selection & probe

### Q: How should the candidate-burst probe be delivered?

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone research doc | `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` produced BEFORE eval; plan-phase locks burst list from it | ✓ |
| Inline at script startup | Probe + skip missing coverage at run time | |
| Skip probe, trust BOOTSTRAP list | Hand-pick 5 candidates directly | |

**User's choice:** Standalone research doc (Recommended)
**Notes:** Matches FEATURES §50 rationale ("Phase 0/1-boundary artifact — any burst without ASF OPERA RTC coverage is a wasted compute run"). Auditable in git history.

### Q: How should cached SAFEs from sibling eval dirs be reused?

| Option | Description | Selected |
|--------|-------------|----------|
| Harness search-path fallback | `eval-rtc-eu/` → `eval-disp-egms/` → `eval-dist-eu/` via helper, no symlink | ✓ |
| Symlinks from sibling cache dirs | `ln -s ../eval-*/input/<safe>.zip eval-rtc-eu/input/` | |
| Re-download per cell | Fully isolated; wastes ~8 GB | |

**User's choice:** Harness search-path fallback (Recommended)
**Notes:** Zero duplication, survives sibling cache cleanup intelligently, keeps each cell self-contained in naming without forcing duplicate bytes.

### Q: How large should the burst list be?

| Option | Description | Selected |
|--------|-------------|----------|
| 5 bursts covering all BOOTSTRAP regimes | Alpine + Scandinavian >55°N + Iberian + Bologna cached + Portuguese fire cached | ✓ |
| 3 mandatory + up to 2 opportunistic | Alpine + Scandinavian + Iberian; cached added if easy | |
| Exactly 3 bursts | Floor: Alpine + Scandinavian + one third regime | |

**User's choice:** 5 bursts covering all BOOTSTRAP regimes (Recommended)
**Notes:** Mandatory regime constraints (RTC-01: ≥1 >1000 m AND ≥1 >55°N) satisfied by Alpine + Scandinavian. Other three distribute terrain diversity without extra download cost.

### Q: Who picks the specific burst IDs?

| Option | Description | Selected |
|--------|-------------|----------|
| Claude drafts, user reviews in plan-phase | Concrete IDs proposed from probe artifact | ✓ |
| User specifies now | Inline list | |
| Derived from probe artifact only | First N covered rows | |

**User's choice:** Claude drafts, user reviews in plan-phase (Recommended)
**Notes:** Lets the probe artifact (D-01) surface live ASF coverage before any burst ID is committed.

---

## Script orchestration

### Q: What shape should the eval script take?

| Option | Description | Selected |
|--------|-------------|----------|
| Single script, declarative burst list | Module-level `BURSTS: list[BurstConfig]` + for-loop | ✓ |
| One script per burst (5 files) | Maps to hypothetical Makefile per-burst targets | |
| Single script + external Makefile per-burst | argparse `--burst` + Makefile explodes | |

**User's choice:** Single script, declarative burst list (Recommended)
**Notes:** Mirrors `run_eval_disp_egms.py` pattern; FEATURES says "fork of run_eval.py"; keeps Phase 1's per-burst-Makefile deferral intact.

### Q: How should the script handle a single burst failing?

| Option | Description | Selected |
|--------|-------------|----------|
| Try/except per burst, accumulate + report | One broken burst doesn't block the others | ✓ |
| Fail-fast | First error aborts script | |
| Per-burst subprocess isolation | Each burst is its own supervisor subprocess | |

**User's choice:** Try/except per burst, accumulate + report (Recommended)
**Notes:** Matches FEATURES "aggregated to '4/5 PASS, 1/5 FAIL'" rendering intent. Supervisor stays the outer failure boundary.

### Q: Sequential or parallel execution across bursts?

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential | opera-rtc already parallelises inside each burst | ✓ |
| Parallel (multiprocessing over bursts) | concurrent.futures / Pool | |
| You decide | Defer to plan-phase | |

**User's choice:** Sequential (Recommended)
**Notes:** Avoids doubling memory pressure (4 GB SAFE + DEM per burst) and re-opening the fork pitfall surface `_mp.py` was designed to close.

### Q: How should resume-safety work across bursts and stages?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-burst skip + per-stage within burst | Whole-burst skip if all outputs cached; else per-stage ensure_resume_safe | ✓ |
| Per-stage only | No burst-level skip | |
| You decide | Defer to plan-phase | |

**User's choice:** Per-burst skip + per-stage within burst (Recommended)
**Notes:** Warm re-run of all 5 bursts finishes in seconds.

---

## metrics.json shape

### Q: What layout for metrics.json in this cell?

| Option | Description | Selected |
|--------|-------------|----------|
| Single aggregate with nested per-burst | One `eval-rtc-eu/metrics.json` with top-level aggregate + `per_burst: [...]` list | ✓ |
| Per-burst files + aggregator at read time | Multiple sidecars, matrix_writer globs | |
| Both per-burst + aggregate | Redundant storage | |

**User's choice:** Single aggregate with nested per-burst (Recommended)
**Notes:** Honours ARCHITECTURE §6 (single metrics_file path per cell, no globbing) while preserving FEATURES per-burst drilldown.

### Q: What should the top-level aggregate summary contain?

| Option | Description | Selected |
|--------|-------------|----------|
| pass_count + total + product_quality/reference_agreement aggregates | Includes worst_rmse_db + worst_r + per_burst list | ✓ |
| Just per_burst list + computed at read | Writer re-aggregates | |
| You decide | Defer | |

**User's choice:** pass_count + total + product_quality/reference_agreement aggregates (Recommended)
**Notes:** Supports cell rendering ("5/5 PASS") and surfaces worst-case for RTC-03 investigation trigger without re-computation in the writer.

### Q: How should the RTC-EU row render in results/matrix.md?

| Option | Description | Selected |
|--------|-------------|----------|
| Single row with 'X/N PASS' + link to CONCLUSIONS | One row per cell; per-burst lives in CONCLUSIONS | ✓ |
| Explode to N rows (one per burst) | 14-row matrix instead of 10 | |
| Summary row + collapsed detail | markdown `<details>` middle-ground | |

**User's choice:** Single row with 'X/N PASS' + link to CONCLUSIONS (Recommended)
**Notes:** Matches FEATURES §52 "aggregated to a single matrix cell" + §106 canonical matrix columns.

### Q: meta.json granularity (provenance sidecar)

| Option | Description | Selected |
|--------|-------------|----------|
| Single cell-level meta.json, per-burst input_hashes nested | One file with top-level provenance + nested per-burst hashes | ✓ |
| Per-burst meta.json | Separate file per burst | |
| You decide | Defer | |

**User's choice:** Single cell-level meta.json, per-burst input_hashes nested (Recommended)
**Notes:** Mirrors metrics.json decision; top-level git_sha / python_version / platform are cell-invariant.

---

## Investigation trigger (RTC-03)

### Q: What concrete RMSE threshold triggers an investigation finding?

| Option | Description | Selected |
|--------|-------------|----------|
| >= 0.15 dB (~3× N.Am. baseline) | Middle-ground; documents meaningful variance without noise | ✓ |
| >= 0.10 dB (~2× N.Am. baseline) | Tighter; may flag normal terrain variance | |
| >= 0.25 dB (halfway to fail) | Looser; may miss real region-specific issues | |
| Case-by-case | No fixed threshold | |

**User's choice:** >= 0.15 dB (~3× N.Am. baseline) (Recommended)
**Notes:** Calibrated from 0.045 dB N.Am. baseline; 0.15 dB still far below 0.5 dB criterion.

### Q: Should the r (Pearson) also have an investigation trigger?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, r < 0.999 also triggers | Dual trigger: RMSE catches bias, r catches structure | ✓ |
| RMSE only | Single metric, simpler | |
| Claude's discretion | Resolve at plan-phase | |

**User's choice:** Yes, r < 0.999 also triggers (Recommended)
**Notes:** N.Am. r = 0.9999; r = 0.997 is still PASS (>0.99) but a 3-order-of-magnitude divergence worth documenting.

### Q: What does an investigation finding look like in CONCLUSIONS_RTC_EU.md?

| Option | Description | Selected |
|--------|-------------|----------|
| Structured sub-section: observation + hypothesis + evidence | Per flagged burst, small (3-part) sub-section | ✓ |
| One-paragraph note only | 1–2 sentences | |
| Full per-burst diagnostic notebook | `notebooks/*_investigation.ipynb` | |

**User's choice:** Structured sub-section: observation + hypothesis + evidence (Recommended)
**Notes:** Notebook is over-scoped for Phase 2; paragraph is too thin for a real regression.

### Q: Should the flagging be automated or manual?

| Option | Description | Selected |
|--------|-------------|----------|
| Automated in eval script | `per_burst[i].investigation_required: bool` written by script | ✓ |
| Manual — human decides at CONCLUSIONS time | Numbers only; prose is human | |
| Claude's discretion | Resolve at plan-phase | |

**User's choice:** Automated in eval script (Recommended)
**Notes:** Automation flags, doesn't replace narrative — human writes the actual investigation text.

---

## Claude's Discretion

Areas where the user gave Claude flexibility for plan-phase (carried into CONTEXT.md `<decisions>` → "Claude's Discretion" subsection):

- Specific burst IDs and sensing dates (D-04)
- Terrain-regime coverage table auto-compute mechanism (DEM read at eval time)
- `BurstConfig` dataclass location (local to script vs shared module)
- Exact OPERA reference discovery helper (`download_reference_with_retry` vs `select_opera_frame_by_utc_hour`)
- Probe query implementation (standalone script vs notebook)
- Multi-zone UTM handling per burst
- Investigation hypothesis list format (narrative vs codified)

## Deferred Ideas

See CONTEXT.md `<deferred>` section for the full list. Highlights:

- Per-burst Makefile targets (Phase 1 deferred, Phase 2 reaffirms)
- Parallel burst execution
- Burst-DB-backed AOI catalogue (v2)
- Shared `BurstConfig` module (promote only if Phase 3/4/6 adopt)
- Per-burst Jupyter investigation notebooks
- Promoting r > 0.999 to a CALIBRATING/BINDING gate (forbidden by RTC-02)
- Cross-version OPERA reference drift detection (v2)
- Automatic regime classification from DEM
- CDSE alternative for OPERA reference (OPERA is ASF-only)
