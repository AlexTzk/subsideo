# Phase 3: CSLC-S1 Self-Consistency + EU Validation - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 consumes Phase 1's shared `validation/stable_terrain.py` + `validation/selfconsistency.py` modules and the frozen `cslc.selfconsistency.*` CALIBRATING criteria to deliver the **first rollout of a new product-quality gate** across three AOIs:

- **SoCal self-consistency** (burst `t144_308029_iw1`, 15 epochs, 14 sequential 12-day IFGs): coherence gate + residual-velocity gate on stable terrain (CSLC-03).
- **Mojave self-consistency** (Coso/Searles Valley primary; 3 fallbacks: Pahranagat / Amargosa / Hualapai): same pair of gates, OR explicit blocker if all 4 AOIs exhausted (CSLC-04).
- **Iberian Meseta EU** (primary: bedrock/sparse-vegetation burst north of Madrid; fallbacks: Alentejo / Massif Central): three independent numbers — OPERA CSLC amplitude sanity (r > 0.6, RMSE < 4 dB), self-consistency coherence + residual (product-quality), and EGMS L2a stable-PS residual velocity (product-quality) (CSLC-05).

Plus **methodology consolidation** of the cross-version phase impossibility finding from `CONCLUSIONS_CSLC_N_AM.md` §5 into `docs/validation_methodology.md` (CSLC-06), paired with the product-quality-vs-reference-agreement distinction section that Phase 4 DISP and Phase 7 REL-03 both depend on.

**Not this phase:**
- Modifying `stable_terrain.py` or `selfconsistency.py` internals (Phase 1 D-modules; Phase 3 is the first consumer).
- Tightening the `cslc.selfconsistency.coherence_min = 0.7` or `residual_mm_yr_max = 5` thresholds based on per-AOI scores (M1 target-creep; gates are CALIBRATING per GATE-05 and require ≥3 data points before promotion to BINDING in v1.2+).
- Single-look phase comparison across isce3 major versions (CONCLUSIONS §5 + P2.4 confirm it yields random noise).
- DISP self-consistency (Phase 4 reuses the same `selfconsistency.py` module but on dolphin-inverted velocities).
- OPERA frame selection methodology + DSWE F1 ceiling sections of `validation_methodology.md` (Phases 5/6 + Phase 7 REL-03 own those).

Phase 3 covers the 4 requirements mapped to it: **CSLC-03** (SoCal), **CSLC-04** (Mojave + fallback-exhaustion blocker), **CSLC-05** (Iberian Meseta 3 numbers), **CSLC-06** (methodology doc CSLC + distinction sections).

</domain>

<decisions>
## Implementation Decisions

### Coherence gate metric + calibration framing (CSLC-03, GATE-05, M5, PITFALLS P2.2)

- **D-01: Gate stat = median of persistently-coherent pixels.** The single BINDING input to the `cslc.selfconsistency.coherence_min = 0.7` criterion is `median_of_persistent` — computed as the median per-pixel-mean-coherence (over the 14 sequential 12-day IFGs) restricted to pixels whose per-IFG coherence exceeds the persistence threshold for every IFG in the stack. Robust to bimodal mask contamination (dunes/playa/fallow pulling mean down) per PITFALLS P2.2 research mitigation. The existing four stats (`mean`, `median`, `p25`, `p75`, `persistently_coherent_fraction`) stay reported alongside in every metrics.json for diagnostic context; only `median_of_persistent` gates PASS/FAIL. Requires a small extension to `selfconsistency.coherence_stats()` to emit `median_of_persistent` as a sixth key — no shape change to the function signature.

- **D-02: Persistence threshold = 0.6 (`selfconsistency.py` default).** `DEFAULT_COHERENCE_THRESHOLD = 0.6` already ships. A pixel is "persistently coherent" if its per-IFG coherence ≥ 0.6 in all 14 IFGs. Literature: individual 12-day S1 IFG coherence on stable bedrock is 0.7–0.85; 0.6 admits most real stable pixels without admitting vegetated/urban outliers. No plan-phase sweep — reuse the ship default.

- **D-03: First-rollout rendering = CALIBRATING cell, no PASS/FAIL until ≥3 data points.** Strict Phase 1 D-03 (matrix_writer italicisation for CALIBRATING cells) + GATE-05 (≥3 data points before BINDING). SoCal is data point 1, Mojave is 2, Iberian is 3. Matrix cell text format: `CALIBRATING: coh=0.XX / resid=Y.Y mm/yr` (not `PASS` / `FAIL`). The `all_pass` boolean in `RTCEUCellMetrics`-style aggregate becomes `all_pass: null` for CALIBRATING cells (requires a small schema extension in Phase 3 — new `status: Literal['PASS', 'FAIL', 'CALIBRATING', 'BLOCKER']` field on per-AOI results, top-level `cell_status: Literal['PASS', 'FAIL', 'CALIBRATING', 'MIXED', 'BLOCKER']`). CONCLUSIONS docs use the exact phrase "calibration data point: <AOI>=<val>" and explicitly do not emit PASS/FAIL prose for CALIBRATING rows.

- **D-04: Gate-stat escape valve = methodology change, not threshold change.** If SoCal's `median_of_persistent` lands clearly below 0.7 through a definitional/contamination reason (P2.2 escape valve), the response is to change the gate STAT — e.g., swap to `persistently_coherent_fraction > 0.5` or `median > 0.7` on a tighter `exclude_mask` — not to lower the 0.7 threshold. The threshold value stays invariant across AOIs. Implementation: add `gate_metric_key: str` to the CRITERIA[`cslc.selfconsistency.coherence_min`] record so the chosen stat is auditable in matrix-writer output; any change to `gate_metric_key` during Phase 3 is documented in the CONCLUSIONS "Calibration Changes" section. PR-ADR policy from Phase 1 D-03 applies unchanged.

### Script organization + matrix cell layout (CSLC-03/04/05, REL-01, ENV-07 discipline)

- **D-05: Two eval scripts `run_eval_cslc_selfconsist_nam.py` + `run_eval_cslc_selfconsist_eu.py`.** Each declares a module-level `AOIS: list[AOIConfig]` (declarative-list pattern from Phase 2 D-05). N.Am. script: `AOIS = [SoCalAOI, MojaveAOI]`; EU script: `AOIS = [IberianAOI]` (with inline fallback metadata — see D-11). Per-AOI try/except isolation per iteration (Phase 2 D-06) so one AOI's failure doesn't block the other(s). Supervisor wraps each script as the outer boundary (Phase 1 D-12); `_mp.configure_multiprocessing()` fires once at the top of `run_cslc()` per script (Phase 1 D-14). Script diff between nam/eu contains only reference-data differences (ENV-07 acceptance).

- **D-06: Two aggregate matrix cells `cslc:nam` + `cslc:eu` with per-AOI nested lists.** Phase 2 D-09 pattern extended: one `eval-cslc-selfconsist-nam/metrics.json` with top-level `pass_count/total`, `product_quality` sub-aggregate (`coherence_gate`, `residual_gate`), `reference_agreement` sub-aggregate (`worst_amp_r`, `worst_amp_rmse_db`), and nested `per_aoi: [SoCalResult, MojaveResult]`. One `eval-cslc-selfconsist-eu/metrics.json` with single-entry `per_aoi: [IberianResult]`. Matrix writer renders two rows: `cslc:nam` → `2/2 CALIBRATING` (or `1/2 CALIBRATING, 1/2 BLOCKER` if Mojave exhausts fallbacks); `cslc:eu` → `1/1 CALIBRATING`. Per-AOI drilldown lives in metrics.json + CONCLUSIONS (not in matrix.md). Preserves Phase 1's 5 products × 2 regions = 10 cells matrix shape.

- **D-07: SoCal + Iberian run amplitude sanity; Mojave skips it.** SoCal: `compare_cslc()` runs against the first-epoch's OPERA CSLC reference → `reference_agreement` sub-result with `amp_r`, `amp_rmse_db` (continuity with v1.0 CONCLUSIONS_CSLC_N_AM.md r=0.79 / RMSE=3.77 dB). Iberian: CSLC-05 explicitly requires amplitude sanity as one of three numbers → `compare_cslc()` against Iberian OPERA CSLC reference. Mojave: `product_quality` only (self-consistency coherence + residual); `reference_agreement` field is null for the Mojave AOI record. Saves one OPERA CSLC download per Mojave fallback — meaningful at up to 4 fallback attempts.

- **D-08: Two CONCLUSIONS files `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` + `CONCLUSIONS_CSLC_EU.md`.** One per script / per matrix cell (mirrors Phase 2's single-file-per-cell pattern). N.Am. doc covers SoCal + Mojave side-by-side (calibration data points 1 + 2, with any fallback attempts logged). EU doc covers Iberian (calibration data point 3 + the three-number schema). Section structure mirrors `CONCLUSIONS_CSLC_N_AM.md` (Objective / Test Setup / Bugs Encountered / Final Validation Results) with new required sections: **Calibration Framing** (M5 discipline statement), **Stable-Mask Sanity Check** (per-AOI coherence histogram + mask-over-optical-basemap PNG per PITFALLS P2.1 mitigation), **Calibration Changes** (any `gate_metric_key` change log — D-04).

### Stack sourcing + AOI probe strategy (CSLC-03/04/05)

- **D-09: SoCal 15 epochs = fresh download, cached under `eval-cslc-selfconsist-nam/input/`.** New cache dir owned by the N.Am. self-consist cell. Query ASF for 15 consecutive S1A IW SLC scenes over burst `t144_308029_iw1` across a 168-day window. Exact 15-epoch window choice (e.g., Nov 2023 – May 2024) is Claude's Discretion at plan-phase (derived from ASF availability + avoiding the POEORB→RESORB transition boundary). ≈ 15 × 7.8 GB = 117 GB download. No cross-cell cache entanglement with Phase 1 DISP-N.Am. — isolation > compute frugality for this cell since SoCal is the calibration anchor for a new gate. OPERA CSLC reference fetched per-epoch for amplitude sanity (D-07) via `select_opera_frame_by_utc_hour` per Phase 1 harness.

- **D-10: Combined probe artifact `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md`.** One committed markdown table covering Mojave + Iberian candidates (SoCal is already locked to `t144_308029_iw1` by CSLC-03). Columns: `aoi, regime, candidate_burst_id, opera_cslc_coverage_2024, egms_l2a_release_2019_2023_stable_ps_count (EU only), expected_stable_pct_per_worldcover, published_insar_stability_ref, cached_safe_fallback_path`. Claude drafts concrete burst IDs via `asf_search` + `earthaccess.search_data(short_name='OPERA_L2_CSLC-S1_V1', ...)` + EGMS L2a per-track CSV inspection; user reviews + locks in plan-phase. Committed before eval runs. Same Phase 2 D-01 discipline — probe doc referenced but not re-run at eval time.

- **D-11: Mojave fallback exhaustion policy = probe all 4, try in probe-locked order, surface blocker if all fail.** Probe artifact pre-ranks Coso/Searles (primary), Pahranagat, Amargosa, Hualapai by `(opera_cslc_coverage_2024) × (expected_stable_pct)`. `run_eval_cslc_selfconsist_nam.py` iterates in that order per `MojaveConfig(fallback_chain=[...])`; each attempt writes a per-attempt `AOIResult(status='PASS'|'CALIBRATING'|'FAIL'|'SKIPPED', attempt_index=N, reason=...)` entry under `mojave.attempts[]`. First CALIBRATING/PASS result wins; supervisor exits 0 on any success. If all 4 fail (every attempt records a non-PASS status), supervisor exits 1 with the Mojave AOI block flagged as `status='BLOCKER'` in metrics.json — matrix cell `cslc:nam` renders `1/2 CALIBRATING, 1/2 BLOCKER`; SoCal calibration row still renders. CSLC-04 met via surfaced blocker, not silent FAIL.

- **D-12: Iberian EGMS L2a stable-PS = `mean_velocity_std < 2 mm/yr` threshold via EGMStoolkit + existing `compare_disp._load_egms_l2a_points()` loader.** BOOTSTRAP §2.3 threshold. EGMS L2a release 2019_2023 per-track CSVs downloaded via EGMStoolkit (pattern from `compare_disp.py`); stable-PS filter is `df[df['mean_velocity_std'] < 2.0]`. New helper `compare_cslc_egms_l2a_residual(our_velocity_raster: Path, egms_csv_paths: list[Path], stable_std_max: float = 2.0) -> float` lives in `validation/compare_cslc.py` (reuses `_load_egms_l2a_points` from compare_disp.py via cross-module import). Residual = `mean(|our_velocity_at_stable_ps - egms_mean_velocity|)` in mm/yr, after reference-frame alignment (subtract stable-set median from our velocity before paired-residual — per PITFALLS P2.3 reuse of `selfconsistency.residual_mean_velocity` anchor logic).

### Methodology doc scope (CSLC-06, PITFALLS P2.4)

- **D-13: Phase 3 writes §1 CSLC cross-version impossibility + §2 product-quality vs reference-agreement distinction.** Two sections in `docs/validation_methodology.md`. Phase 3 owns only the methodological findings for which it has authoritative evidence: (a) CSLC cross-version from v1.0 CONCLUSIONS_CSLC_N_AM.md §5 + Phase 3's own Iberian + SoCal amplitude-only validation runs; (b) product-quality vs reference-agreement distinction from Phase 1 GATE-01..05 scaffolding + Phase 3's own Iberian row showing three independent numbers. Phase 7 REL-03 adds §3 OPERA frame selection + §4 DSWE F1 ≈ 0.92 ceiling + §5 cross-sensor precision-first framing. Each phase writes what it has evidence for; no stub scaffolding.

- **D-14: §1 Cross-version section = structural argument (isce3 interpolation kernel) + CONCLUSIONS §5 diagnostic evidence.** Structural argument first (closes the door permanently on re-attempt anti-pattern P2.4): between isce3 0.15 and 0.25, the SLC interpolation kernel itself changed — two CSLCs computed from the same SLC with different interpolation kernels produce different absolute phase values at every pixel, and no post-processing phase-screen correction can recover that. Then diagnostic evidence: CONCLUSIONS_CSLC_N_AM.md §5.3 documented that removing carrier (coh 0.002), flattening (coh 0.002), and both together (coh 0.002) all yielded random-noise coherence. References the upstream isce3 0.15→0.19 changelog entry on SLC interpolation + PITFALLS P2.4. Contains a "do not re-attempt with additional corrections" policy statement audible to future contributors.

- **D-15: `docs/validation_methodology.md` evolution policy = append-only per phase.** Phase 4 appends §3 DISP ramp-attribution methodology (its own authoritative evidence from PHASS N.Am./EU re-runs). Phases 5/6 append §4 DSWE F1 ceiling + §5 cross-sensor precision-first framing. Phase 7 REL-03 writes the top-level table of contents + cross-section links + does final consistency pass across all 5 sections. No stub scaffolding created in Phase 3; no Phase 3 ownership of later sections. Prevents stub-rot. Each phase's append is a single PR with the new section inserted at its final position.

### Claude's Discretion (for plan-phase)

- **Exact SoCal 15-epoch sensing window** (D-09) — Claude picks from ASF availability for burst `t144_308029_iw1` at plan-phase, preferring a 168-day window that spans clean POEORB coverage (no RESORB-only epochs) and avoids the Nov 2023 Sentinel-1B end-of-life transition. User reviews proposed epoch list before `AOIS` list is committed. First SoCal epoch's OPERA CSLC is the amplitude-sanity reference (D-07).

- **Residual-velocity computation chain** — whether to run MintPy's full `smallbaselineApp.py` inversion or a simple per-pixel linear-fit over the 14 IFGs. Research FEATURES line 60 mentions both ("MintPy-inverted (or simple velocity-fit) time-series"). Start with the simple linear fit in `compute_residual_velocity(cslc_stack) -> velocity_mm_yr_raster` helper in `validation/selfconsistency.py`; promote to MintPy only if linear-fit variance on SoCal indicates the simpler method is below the 5 mm/yr bar's resolution. Linear-fit has no ERA5 tropospheric-correction dependency (pyaps3 not required for Phase 3).

- **US stable-pixel operational definition for CSLC-03** — "OPERA-CSLC-derived stable pixels" from the requirement text is ambiguous. Plan-phase resolves as: apply `stable_terrain.build_stable_mask` to the SoCal burst (WorldCover class 60 + slope < 10° + 5 km coast buffer + 500 m water buffer), yielding the boolean stable mask; then optionally intersect with pixels whose OPERA CSLC amplitude is itself stable across the 15 epochs (inter-epoch amplitude std < configurable threshold) — the latter is a belt-and-braces check, not a first-class requirement. Primary: subsideo's own `stable_terrain.build_stable_mask` output. OPERA-side amplitude-stability intersection is reported-alongside, not gate-critical.

- **Boxcar window size for per-IFG coherence** — typical S1 is 5×5 (research FEATURES line 59 "typical 5×5"); whether to expose as tunable `boxcar_px: int = 5` parameter on `compute_ifg_coherence_stack(cslc_stack)` helper or hardcode. Start hardcoded at 5; expose if calibration needs tuning across AOIs.

- **AOIConfig / MojaveConfig dataclass shape** — whether to live local-to-script (Phase 2 D-05 default) or promote to shared `validation/eval_types.py` (Phase 2 deferred). Start local-to-script; promote if Phase 4 DISP eval adopts the same shape.

- **WorldCover fetch helper implementation** — `fetch_worldcover_class60(bbox, out_dir)` reading from `s3://esa-worldcover/v200/2021/` (public-read, no credentials) per FEATURES line 61. New helper in `validation/stable_terrain.py` OR new `data/worldcover.py` module. Claude picks — the former is load-bearing-here-only, the latter is more extensible for DSWx use in Phase 6.

- **Coastline + water-body data source** — `stable_terrain.build_stable_mask` accepts optional geometries; Phase 3 must supply them for the coast/water buffers to actually fire. Natural Earth coastline (10m scale, BSD-style license, ~20 MB) via the `naturalearth` PyPI package OR OSM coastline tiles. Natural Earth is simpler (no tile assembly); OSM has higher fidelity. Start Natural Earth; revisit if buffer excludes too-much/too-little on SoCal.

- **Probe artifact query implementation** — hand-run Python script `scripts/probe_cslc_aoi_candidates.py` (Phase 2 precedent) OR gsd-sdk query OR notebook. Hand-run script matches v1.0 style; committed as sub-deliverable per plan-phase output.

- **Supervisor `EXPECTED_WALL_S` budget per script** — 15 epochs × (~40 min/epoch cold CSLC + amp-sanity) ≈ 12 h for N.Am. (SoCal) + up to 4 × 12 h = 48 h for Mojave fallback-chain worst case → cap at ~16 h per cell-script with per-AOI budget guards; plan-phase decides `EXPECTED_WALL_S` vs hard timeout. Warm re-run (all CSLCs cached) target: ≤ 5 min per cell.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source-of-truth scope (read first)

- `.planning/ROADMAP.md` §Phase 3 — goal, 4 success criteria, 4 requirements (CSLC-03..06), internal-ordering notes, planning-artifact flag on coherence metric choice.
- `.planning/REQUIREMENTS.md` §CSLC-03..06 — full text of the 4 requirements + BOOTSTRAP §2 stable-PS threshold (`mean_velocity_std < 2 mm/yr`).
- `.planning/PROJECT.md` — pass criteria (CSLC amplitude r > 0.6, RMSE < 4 dB; self-consistency coh > 0.7, residual < 5 mm/yr), metrics-vs-targets discipline v1.1 paragraph, cross-version phase impossibility recorded as a Key Decision.
- `.planning/STATE.md` — v1.1 accumulated decisions; Phase 3 research-flagged coherence metric choice (MEDIUM uncertainty).

### Phase 1/2 CONTEXT (REQUIRED for understanding harness + criteria + aggregate schema)

- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-CONTEXT.md` — D-01..D-19: criteria.py shape + frozen-dataclass + `Literal['BINDING', 'CALIBRATING']` + `binding_after_milestone`; split `ProductQualityResult` / `ReferenceAgreementResult` with `measurements` + `criterion_ids` + computed pass/fail; shared `stable_terrain.py` + `selfconsistency.py` modules; matrix_writer CALIBRATING italicisation (D-03); `cslc.selfconsistency.coherence_min=0.7` + `residual_mm_yr_max=5` CALIBRATING criteria already populated (D-04).
- `.planning/phases/02-rtc-s1-eu-validation/02-CONTEXT.md` — D-01..D-15: standalone probe artifact pattern (D-01), cached-SAFE harness fallback (D-02), declarative `BURSTS` list + per-burst try/except (D-05..D-08), aggregate metrics.json with `per_burst` nested list + top-level summary (D-09, D-10), matrix row `X/N PASS` + CONCLUSIONS link (D-11), cell-level meta.json with nested per-burst input hashes (D-12), `INVESTIGATION_TRIGGER` Criterion-type extension (D-13 — Phase 3 adds a parallel new `status: Literal['PASS', 'FAIL', 'CALIBRATING', 'BLOCKER']` field, not a new Criterion type).

### Phase 3 research (authoritative for HOW)

- `.planning/research/SUMMARY.md` §Phase 3 (lines 162–167) — 4-5 day effort estimate; watchout list P2.1/P2.2/P2.3/P2.4/M5; 3 eval scripts + 3 CONCLUSIONS + methodology cross-version section framing; Research Flag §1 coherence metric choice (Phase 3 planning decision — now resolved D-01).
- `.planning/research/FEATURES.md` §Phase 2 CSLC self-consistency gate (lines 55–65) — table-stakes deliverables: self-consistency coherence computation shape + stable-PS residual velocity computation + WorldCover + SRTM slope mask builder + `run_eval_cslc_selfconsistency.py` + Mojave AOI selection + `run_eval_cslc_eu.py` + `docs/validation_methodology.md` cross-version section; line 60 BOOTSTRAP §2 stable-PS threshold source text + MintPy-or-linear-fit note; line 61 WorldCover S3 bucket (`s3://esa-worldcover/v200/2021/`, public-read).
- `.planning/research/PITFALLS.md` §P2.1 (lines 276–301) — stable-mask contamination mitigation (coast 5km + water 500m buffers + exclude_mask optional per-AOI; median-not-mean report; stability-mask-sanity-check artifact); §P2.2 (lines 305–326) — mean-vs-median-vs-persistently-coherent-fraction (the gate metric research flag — resolved D-01); §P2.3 (lines 330–353) — residual velocity reference-frame alignment (already in `selfconsistency.residual_mean_velocity` median anchor); §P2.4 (lines 357–383) — cross-version phase re-attempt anti-pattern + structural isce3 interpolation-kernel argument; §M5 (lines 118–133) — too-tight-first-rollout (CALIBRATING framing for data point 1); §M1 (lines 28–45) — target-creep prevention (criteria immutability even when EU differs from N.Am.).
- `.planning/research/ARCHITECTURE.md` §6 — matrix_manifest.yml + per-eval metrics.json sidecar pattern; §1 — harness public API (`select_opera_frame_by_utc_hour`, `download_reference_with_retry`, `ensure_resume_safe`, `credential_preflight`, `bounds_for_burst`); §Failure-Mode Boundaries — `validation/selfconsistency.py` imports OK from `validation/compare_cslc.py`; no cycle.
- `.planning/research/STACK.md` — rio-cogeo 6.0.0 via `_cog.py` (ref for saving self-consistency product rasters if emitted); EGMStoolkit 0.2.15 for L2a CSV download; pyaps3 0.3.6 only if MintPy inversion chosen for residual (D-Claude's-Discretion).

### v1.0 CONCLUSIONS (context for why the methodology section exists)

- `CONCLUSIONS_CSLC_N_AM.md` §5 — cross-version phase impossibility evidence (carrier removal / flattening / both = coherence ≈ 0.002) — D-14 §1 consolidation source.
- `CONCLUSIONS_CSLC_N_AM.md` §1.1 — amplitude-based criteria (r > 0.6, RMSE < 4 dB) rationale.
- `CONCLUSIONS_CSLC_N_AM.md` §2 — SoCal burst + scene reference (burst `t144_308029_iw1`, SAFE `S1A_IW_SLC__1SDV_20240624T140113..._20E5.zip`) — D-09 SoCal fresh-download fork source.
- `CONCLUSIONS_CSLC_N_AM.md` §Bug 6 — sub-pixel grid misalignment resolution (relevant for comparing our 15-epoch stack against per-epoch OPERA CSLC refs for D-07 amplitude sanity).

### v1.0 precedent files to match (existing conventions)

- `src/subsideo/validation/stable_terrain.py` — Phase 1 D-module (208 LOC); `build_stable_mask(worldcover, slope_deg, coastline, waterbodies, coast_buffer_m=5000, water_buffer_m=500, slope_max_deg=10)` returns `(H, W) bool`. Phase 3 is the first consumer. Pure-function module, no I/O, lazy-imports conda-forge deps. No modification needed in Phase 3.
- `src/subsideo/validation/selfconsistency.py` — Phase 1 D-module (165 LOC); `coherence_stats(ifgrams_stack, stable_mask, coherence_threshold=0.6)` returns dict with 5 stats; `residual_mean_velocity(velocity_mm_yr, stable_mask, frame_anchor='median')` returns float. Phase 3 extends with (a) `median_of_persistent` as 6th stat key in `coherence_stats`, (b) optional `compute_residual_velocity(cslc_stack_paths, stable_mask) -> velocity_raster` helper if D-Claude's-Discretion linear-fit route chosen. One-time additive, not a rewrite.
- `run_eval_cslc.py` (209 LOC) — N.Am. amplitude-only CSLC eval, 1 scene. Fork source for `run_eval_cslc_selfconsist_nam.py`; upgrades to 15-epoch stack + declarative `AOIS` list + self-consistency pipeline.
- `src/subsideo/validation/compare_cslc.py` (212 LOC) — amplitude-based `ReferenceAgreementResult` emitter (already migrated to split-dataclass per Phase 1 D-09). Phase 3 consumes unchanged for amplitude sanity; adds new top-level function `compare_cslc_egms_l2a_residual(our_velocity, egms_csv_paths, stable_std_max=2.0)` (D-12).
- `src/subsideo/validation/compare_disp.py` §`_load_egms_l2a_points()` (lines 187–235) — EGMS L2a CSV reader (schema: `easting`/`northing` or `longitude`/`latitude` + `mean_velocity` + `mean_velocity_std`; handles EPSG:3035 legacy releases). Cross-module import from `compare_cslc.py` for D-12.
- `src/subsideo/validation/compare_disp.py` §`compare_disp_egms_l2a()` (lines 239–380) — PS-point sampling pattern (rasterio windowed read at PS coordinates + paired-residual metrics). Template for D-12 new function; Iberian residual computation mirrors the sampling logic at stable-PS subset instead of all-PS.
- `src/subsideo/validation/criteria.py` (Phase 1 D-04) — already has `cslc.selfconsistency.coherence_min = 0.7` + `residual_mm_yr_max = 5` as `CALIBRATING` with `binding_after_milestone='v1.2'`. Phase 3 adds: (a) `gate_metric_key: str = 'median_of_persistent'` as a field on these two entries (D-04), (b) `cslc.amplitude_r_min = 0.6` + `amplitude_rmse_db_max = 4.0` already exist as BINDING (unchanged).
- `src/subsideo/validation/matrix_schema.py` — Pydantic v2 base `CellMetrics` + Phase 2's `RTCEUCellMetrics` subtype. Phase 3 adds `CSLCSelfConsistNAMCellMetrics` + `CSLCSelfConsistEUCellMetrics` extending the base (per-AOI nested, top-level product_quality + reference_agreement sub-aggregates, `cell_status: Literal['PASS', 'FAIL', 'CALIBRATING', 'MIXED', 'BLOCKER']`).
- `src/subsideo/validation/matrix_writer.py` — Phase 2 extended with RTC-EU render branch. Phase 3 adds `cslc:nam` + `cslc:eu` render branches with `X/N CALIBRATING` formatting + italicisation (Phase 1 D-03 CALIBRATING cell discipline).
- `src/subsideo/validation/supervisor.py` — Phase 1 subprocess wrapper + mtime-staleness watchdog. Phase 3's 2 scripts declare `EXPECTED_WALL_S` at module level per Phase 1 D-11 convention.
- `src/subsideo/validation/harness.py` — Phase 1 5 helpers. Phase 3 is the 4th production consumer (after Phase 1 pilot `run_eval.py`, Phase 2 `run_eval_rtc_eu.py`, Phase 1 migration of remaining 6 v1.0 scripts). May add a helper if the 15-epoch OPERA CSLC batch-fetch pattern recurs (Claude's Discretion).
- `src/subsideo/products/cslc.py` — `run_cslc(safe_paths, orbit_path, dem_path, burst_ids, output_dir, burst_database_file)` entry point. Unchanged in Phase 3 (Phase 1 D-09 big-bang migration already landed; 4 monkey-patches already deleted per ENV-02). `_mp.configure_multiprocessing()` fires once at the top of `run_cslc()` per Phase 1 D-14.
- `src/subsideo/data/dem.fetch_dem`, `data/orbits.fetch_orbit` — cached helpers per AOI.
- `CONCLUSIONS_CSLC_N_AM.md` — template for `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` / `CONCLUSIONS_CSLC_EU.md` section structure.
- `CONCLUSIONS_RTC_EU.md` — template for the multi-AOI aggregate CONCLUSIONS section structure (how SoCal + Mojave coexist in one file).
- `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` — template for `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md` probe artifact (D-10).
- `results/matrix_manifest.yml` — already lists `cslc:nam` + `cslc:eu` cell entries per Phase 1 D-08. Phase 3 fills the referenced paths at runtime; no manifest edits.
- `Makefile` — already has `eval-cslc-nam` + `eval-cslc-eu` targets per Phase 1 D-08. Phase 3 creates the referenced scripts.

### External library refs (read as-needed during plan-phase)

- `opera_utils.burst_frame_db.get_burst_id_geojson()` — SoCal burst footprint for `bounds_for_burst`.
- `asf_search.search(platform='SENTINEL-1A', processingLevel='SLC', ...)` — 15-epoch SAFE discovery for SoCal D-09 + Mojave candidates.
- `earthaccess.search_data(short_name='OPERA_L2_CSLC-S1_V1', ...)` — OPERA CSLC reference discovery per epoch for SoCal + Iberian amplitude sanity (D-07).
- `EGMStoolkit` 0.2.15 — EGMS L2a per-track CSV download for Iberian EGMS stable-PS residual (D-12). Release 2019_2023 EPSG:3035 legacy coordinate handling already in `_load_egms_l2a_points`.
- `s3://esa-worldcover/v200/2021/` — public-read WorldCover bucket for `fetch_worldcover_class60` (Claude's Discretion helper).
- Natural Earth `naturalearth` PyPI package — coastline + water-body geometries for stable_terrain buffers (Claude's Discretion data source).
- `pyaps3 >= 0.3.6` — only if MintPy inversion chosen for residual (Claude's Discretion); requires `~/.cdsapirc` ERA5 credentials. Linear-fit route does NOT require this.

### No external ADR/spec docs for Phase 3

Phase 3 is codebase-internal validation work; no external spec consumed. All canonical refs above are internal planning docs, v1.0 CONCLUSIONS, or upstream library docs referenced at plan time.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`src/subsideo/validation/stable_terrain.py` (208 LOC)** — Phase 1 D-module. `build_stable_mask(worldcover, slope_deg, coastline, waterbodies, coast_buffer_m=5000, water_buffer_m=500, slope_max_deg=10)` returns boolean mask. Lazy-imports geopandas/shapely/rasterio inside `_buffered_geometry_mask`. Phase 3 consumes unchanged for all three AOIs.
- **`src/subsideo/validation/selfconsistency.py` (165 LOC)** — Phase 1 D-module. `coherence_stats(ifgrams_stack, stable_mask, coherence_threshold=0.6)` returns 5-stat dict; `residual_mean_velocity(velocity_mm_yr, stable_mask, frame_anchor='median')` returns float with reference-frame alignment. Phase 3 additively extends with `median_of_persistent` 6th key and optional `compute_residual_velocity(cslc_stack, stable_mask)` linear-fit helper.
- **`src/subsideo/validation/compare_cslc.py` (212 LOC)** — amplitude-based ReferenceAgreementResult emitter (already Phase 1 migrated). Phase 3 consumes unchanged for D-07 amplitude sanity; adds `compare_cslc_egms_l2a_residual()` new function for D-12.
- **`src/subsideo/validation/compare_disp.py` §`_load_egms_l2a_points` (lines 187–235)** — reusable via cross-module import from `compare_cslc.py` for D-12 Iberian EGMS residual.
- **`src/subsideo/validation/compare_disp.py` §`compare_disp_egms_l2a` (lines 239–380)** — template for D-12 PS-point sampling logic at stable-PS subset.
- **`src/subsideo/validation/harness.py` 5 helpers** — Phase 3 is the 4th consumer. No new helpers required unless 15-epoch OPERA CSLC batch-fetch pattern warrants (Claude's Discretion).
- **`src/subsideo/validation/criteria.py`** — `cslc.selfconsistency.coherence_min=0.7` + `residual_mm_yr_max=5` already CALIBRATING entries (Phase 1 D-04). Phase 3 adds `gate_metric_key: str = 'median_of_persistent'` field (D-04) — additive extension to the `Criterion` frozen dataclass.
- **`src/subsideo/validation/matrix_schema.py`** — Pydantic v2 base. Phase 3 adds `CSLCSelfConsistNAMCellMetrics` + `CSLCSelfConsistEUCellMetrics` + an `AOIResult` base type (mirroring Phase 2's `BurstResult`).
- **`src/subsideo/validation/supervisor.py`** — Phase 1 subprocess wrapper. Phase 3's two scripts declare `EXPECTED_WALL_S` per Phase 1 D-11.
- **`run_eval_cslc.py` (209 LOC)** — fork source for `run_eval_cslc_selfconsist_nam.py` (SoCal + Mojave) + `run_eval_cslc_selfconsist_eu.py` (Iberian). Structure: `credential_preflight` → per-AOI loop → OPERA ref fetch (Earthaccess) → SAFE fetch (asf_search) → DEM/orbit fetch → `run_cslc` → `compare_cslc` + self-consistency.
- **`CONCLUSIONS_CSLC_N_AM.md` (319 LOC)** — section-structure template for Phase 3's 2 new CONCLUSIONS files.
- **`.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md`** — template for Phase 3 probe artifact (D-10).

### Established Patterns

- **Two-layer install + lazy imports** — Phase 3 new code follows Phase 1 convention (conda-forge deps imported inside function bodies, not at module top). Matters for `compute_ifg_coherence_stack` etc. that would otherwise hit h5py at module top.
- **`if __name__ == "__main__":` guard + `credential_preflight` first + harness consumption** — non-negotiable per Phase 1 `_mp` precondition + Phase 2 D-05 script template. Both Phase 3 scripts follow this shape.
- **Per-AOI try/except accumulate** (Phase 2 D-06) — each AOI iteration wrapped; failure records error + continues. Phase 3 extends with `attempts[]` sub-list for Mojave fallback chain (D-11).
- **Declarative `AOIS` list** (Phase 2 D-05) — module-level list of `AOIConfig` dataclass entries; iteration invariant per AOI.
- **Supervisor subprocess wrap via Makefile + `EXPECTED_WALL_S`** (Phase 1 D-12) — Makefile invokes `python -m subsideo.validation.supervisor run_eval_cslc_selfconsist_nam.py`; supervisor AST-parses the constant.
- **Aggregate metrics.json + nested per-AOI list** (Phase 2 D-09, D-10) — Phase 3 reuses for `per_aoi: list[AOIResult]` with top-level product_quality + reference_agreement sub-aggregates.
- **Cell-level meta.json with nested per-AOI input hashes** (Phase 2 D-12) — Phase 3 records per-AOI SAFE/DEM/orbit/OPERA-ref SHA256s + per-epoch list for the 15-epoch stack.
- **Matrix writer manifest-authoritative** — Phase 3 never globs CONCLUSIONS_*.md or eval-*/metrics.json; all paths via `results/matrix_manifest.yml` entries.
- **CALIBRATING criteria visible italicisation** (Phase 1 D-03) — matrix cell for `cslc:nam` + `cslc:eu` uses italic formatting while any AOI row reads `CALIBRATING`.
- **Loguru + pydantic-settings + hatchling** — unchanged; Phase 3 follows v1.0 conventions.

### Integration Points

- **`src/subsideo/validation/selfconsistency.py`** — additive edits: new `median_of_persistent` key in `coherence_stats` return dict, optional new `compute_residual_velocity(cslc_stack_paths, stable_mask)` helper (Claude's Discretion: linear-fit route). No signature changes, no field removals.
- **`src/subsideo/validation/compare_cslc.py`** — additive edits: new top-level `compare_cslc_egms_l2a_residual(our_velocity_raster, egms_csv_paths, stable_std_max=2.0) -> float` function using cross-module import from `compare_disp.py::_load_egms_l2a_points`.
- **`src/subsideo/validation/criteria.py`** — additive edits: `gate_metric_key` field on two existing `CALIBRATING` entries (D-04); otherwise unchanged.
- **`src/subsideo/validation/matrix_schema.py`** — additive new Pydantic types: `AOIResult`, `CSLCSelfConsistNAMCellMetrics`, `CSLCSelfConsistEUCellMetrics`; adds `cell_status: Literal['PASS', 'FAIL', 'CALIBRATING', 'MIXED', 'BLOCKER']` as an enum literal for use in these cells and potentially elsewhere.
- **`src/subsideo/validation/matrix_writer.py`** — additive new render branches for `cslc:nam` + `cslc:eu` cell types, including italicised-CALIBRATING rendering.
- **`Makefile`** — unchanged; targets `eval-cslc-nam` + `eval-cslc-eu` already present from Phase 1 D-08.
- **`results/matrix_manifest.yml`** — unchanged; `cslc:nam` + `cslc:eu` cell entries already committed in Phase 1.
- **`.gitignore`** — existing `eval-*/` rule auto-ignores new cache dirs.
- **New files**:
  - `run_eval_cslc_selfconsist_nam.py` at repo root (SoCal + Mojave fallback chain).
  - `run_eval_cslc_selfconsist_eu.py` at repo root (Iberian + fallbacks).
  - `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` at repo root (post-eval).
  - `CONCLUSIONS_CSLC_EU.md` at repo root (post-eval).
  - `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md` (pre-eval probe artifact).
  - `docs/validation_methodology.md` (CSLC-06; new file with §1 + §2 only, per D-13 append-only policy).
  - Optional: `scripts/probe_cslc_aoi_candidates.py` that produces the probe artifact; committed as sub-deliverable per Claude's Discretion.
  - Optional: `data/worldcover.py` OR inline in `validation/stable_terrain.py` — Claude's Discretion per plan-phase (WorldCover fetch helper).

### Script / Matrix Flow (data shape)

```
run_eval_cslc_selfconsist_nam.py:
  configure_multiprocessing()
  credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])
  AOIS = [SoCalAOI (locked), MojaveAOI (fallback_chain=[Coso, Pahranagat, Amargosa, Hualapai])]
  per_aoi: list[AOIResult] = []
  for aoi in AOIS:
    if aoi has fallback_chain:
      attempts = []
      for candidate in aoi.fallback_chain:
        try:
          result = run_one_aoi(candidate)  # CSLC stack + compare + self-consistency
          attempts.append(result)
          if result.status in ('PASS', 'CALIBRATING'): break
        except Exception as e:
          attempts.append(AOIResult(status='FAIL', error=repr(e), ...))
      per_aoi.append(AOIResult(name=aoi.name, attempts=attempts,
                               status=attempts[-1].status if any_success else 'BLOCKER', ...))
    else:
      try:
        per_aoi.append(run_one_aoi(aoi))
      except Exception as e:
        per_aoi.append(AOIResult(status='FAIL', error=repr(e), ...))

  aggregate: CSLCSelfConsistNAMCellMetrics = reduce(per_aoi)
  write eval-cslc-selfconsist-nam/metrics.json (aggregate + per_aoi nested)
  write eval-cslc-selfconsist-nam/meta.json   (provenance + nested per_aoi per_epoch hashes)

where run_one_aoi(aoi):
  bounds = bounds_for_burst(aoi.burst_id)
  worldcover = fetch_worldcover_class60(bounds, cache_dir)
  dem = fetch_dem(bounds, cache_dir)
  slope = gdal.slope(dem) -> np.ndarray
  coastline, waterbodies = natural_earth_for_bounds(bounds)
  stable_mask = build_stable_mask(worldcover, slope, coastline, waterbodies,
                                   coast_buffer_m=5000, water_buffer_m=500)
  # 15 epochs
  for epoch in SENSING_WINDOW[aoi]:
    safe = find_cached_safe_or_download(epoch)
    orbit = fetch_orbit(safe)
    opera_ref = select_opera_frame_by_utc_hour(aoi.burst_id, epoch)  # SoCal+Iberian only (D-07)
    our_cslc = run_cslc(safe, orbit, dem, [aoi.burst_id], output_dir)
  ifgrams = compute_ifg_coherence_stack(our_cslcs, boxcar_px=5)  # (14, H, W)
  coh_stats = coherence_stats(ifgrams, stable_mask)  # 6 stats incl. median_of_persistent
  velocity = compute_residual_velocity(our_cslcs, stable_mask)  # mm/yr raster
  residual = residual_mean_velocity(velocity, stable_mask, frame_anchor='median')
  pq = ProductQualityResult(
    measurements={"coherence_median_of_persistent": coh_stats['median_of_persistent'],
                  "residual_mm_yr": residual,
                  # diagnostics
                  "coherence_mean": coh_stats['mean'],
                  "coherence_median": coh_stats['median'],
                  "coherence_p25": coh_stats['p25'],
                  "coherence_p75": coh_stats['p75'],
                  "persistently_coherent_fraction": coh_stats['persistently_coherent_fraction']},
    criterion_ids=["cslc.selfconsistency.coherence_min", "cslc.selfconsistency.residual_mm_yr_max"],
  )
  ra = compare_cslc(...)  # SoCal + Iberian only (D-07); None for Mojave
  status = 'CALIBRATING'  # first rollout of gate (D-03); will be PASS/FAIL once ≥3 data points
  return AOIResult(aoi=aoi, status=status, product_quality=pq, reference_agreement=ra, ...)
```

### Iberian EU Flow (additional to above)

```
run_eval_cslc_selfconsist_eu.py adds EGMS L2a step for Iberian:
  egms_csvs = EGMStoolkit.download_l2a(bbox=iberian_bounds, release="2019_2023",
                                        output_dir="eval-cslc-selfconsist-eu/egms/")
  egms_residual = compare_cslc_egms_l2a_residual(velocity, egms_csvs, stable_std_max=2.0)
  pq.measurements["egms_l2a_stable_ps_residual_mm_yr"] = egms_residual
  pq.criterion_ids.append("cslc.egms_l2a.residual_mm_yr_max")  # CALIBRATING, 5 mm/yr bar per CSLC-05
```

</code_context>

<specifics>
## Specific Ideas

- **Gate metric choice resolves the P2.2 research flag first** — the Phase 3 work has to ship `median_of_persistent` as a 6th key in `coherence_stats` before any AOI eval runs; otherwise SoCal calibration happens against whatever the default key is, setting an expectation the gate should not own. Land the `selfconsistency.py` extension as plan-phase's first task.
- **SoCal is the calibration anchor, not just a third AOI** — burst `t144_308029_iw1` has v1.0 amplitude r=0.79 / RMSE=3.77 dB already on record. If Phase 3's amplitude-sanity re-run on the first epoch reads materially different (e.g., r < 0.7 or RMSE > 4.5), that's a regression signal worth an investigation note in CONCLUSIONS_CSLC_SELFCONSIST_NAM.md — a form of Phase 2's investigation-trigger discipline applied retrospectively. Not a new CRITERIA entry; just a narrative hook.
- **Iberian is where three numbers visibly coexist** — CSLC-05's explicit list (amp sanity r/RMSE, self-consistency coh, EGMS L2a residual) is the clearest single example of the product-quality vs reference-agreement distinction the milestone ships. `docs/validation_methodology.md` §2 (D-13) cites the Iberian row as its motivating example.
- **Mojave fallback policy has a 48 h worst-case compute budget** — 4 × ~12 h per-fallback CSLC stack. Supervisor `EXPECTED_WALL_S` for the N.Am. script is sized for this case; plan-phase may choose to fail fast on the first Mojave fallback and require manual re-trigger of the next candidate (shorter compute budget, more human-in-loop friction). Current decision: probe-ordered sequential per D-11.
- **`median_of_persistent` is NOT a new criterion; it IS the gate stat for an existing criterion** — `cslc.selfconsistency.coherence_min` stays at 0.7 + CALIBRATING + `binding_after_milestone='v1.2'`. `gate_metric_key='median_of_persistent'` is new metadata on that criterion. No GATE-05 re-count of data points; the data points remain "SoCal calibration run, Mojave calibration run, Iberian calibration run."
- **Cross-version phase re-attempt anti-pattern is the #1 risk to P2.4** — a new contributor reading CONCLUSIONS_CSLC_N_AM.md §5 may not internalise the isce3 interpolation-kernel argument. Phase 3's §1 of `docs/validation_methodology.md` puts the structural argument BEFORE the diagnostic evidence specifically to close this door (D-14). The methodology doc is for us-future-selves and external contributors.

</specifics>

<deferred>
## Deferred Ideas

- **P2.4 isce3 minor-version kernel-change diagnostic experiment** (0.19 vs 0.25 / 0.25.8 vs 0.25.10 / 0.25.10 vs current-latest) — research-named as LOW confidence, 1.5–2 days work, NOT a milestone gate. Adding would strengthen §1 but is not required; revisit in v1.2 if the door doesn't stay closed.
- **MintPy full SBAS inversion for residual velocity** — starts as linear-fit per Claude's Discretion; promote to MintPy only if linear-fit variance > gate headroom. Full MintPy adds `pyaps3 >= 0.3.6` + `~/.cdsapirc` dependency surface to Phase 3; deferred unless needed.
- **Intersect subsideo's stable_mask with OPERA-CSLC amplitude-stability mask** — belt-and-braces check per Claude's Discretion US stable-pixel definition; report-alongside, not gate-critical in Phase 3. Revisit if mask-contamination diagnostics warrant.
- **Tunable boxcar window size per AOI** — typical 5×5 Sentinel-1; plan-phase hardcodes. Expose if calibration needs tuning.
- **Shared `AOIConfig` / `AOIResult` in `validation/eval_types.py`** — stays local to each script per Phase 2 D-05 default; promote if Phase 4 DISP eval adopts the same shape. No pre-commit.
- **Burst-DB-backed AOI catalogue** (FEATURES Differentiators §126) — "attractive but Phase-scope creep; better as v2." Phase 3 hand-picks via BOOTSTRAP candidates + probe, not catalogue query.
- **Mojave "fail fast + manual re-trigger" alternative fallback policy** — current D-11 is auto-sequential; plan-phase could introduce a flag for human-in-loop between fallback attempts. Deferred unless compute-budget pressure materialises.
- **Residual velocity chain handling of the POEORB→RESORB transition epoch** — plan-phase SoCal window choice avoids RESORB epochs; if unavoidable, plan-phase adds an epoch-quality-flag column to AOIResult. Not needed unless forced.
- **Phase-coherence cross-check on isce3-equivalent-version stacks** — v1.0 CONCLUSIONS §6 suggested comparing DISP time-series across OPERA vs subsideo CSLC stacks as a scientific-equivalence test. Phase 3 scope is single-chain self-consistency; cross-chain DISP comparison is Phase 4's DISP N.Am./EU re-run, not Phase 3.
- **Natural Earth vs OSM for coastline + water-body geometries** — Natural Earth chosen at Claude's Discretion; revisit to OSM if Natural Earth buffer exclusion is too coarse/fine on any AOI.
- **WorldCover fetch helper placement** (`data/worldcover.py` vs inline in `validation/stable_terrain.py`) — Claude's Discretion at plan-phase.
- **P5.4 drought-year wet/dry analog for CSLC** — not directly applicable to CSLC (Phase 6 DSWx concern); noted only because the Iberian Meseta 2022 drought-year signal may also affect stable-terrain Mediterranean vegetation coherence — research doesn't flag this but plan-phase may want a wet-vs-dry sensing-window test if Iberian calibration data point is anomalous.
- **Extending cell_status to other v1.1 cells retroactively** — Phase 3 introduces `Literal['PASS', 'FAIL', 'CALIBRATING', 'MIXED', 'BLOCKER']`; Phase 2 RTC-EU cell currently uses `PASS` / `FAIL` only. Unifying retroactively would touch Phase 2 schema; deferred — Phase 7 REL-01 consolidates cell_status semantics across all 10 cells.

### Reviewed Todos (not folded)

No pending todos matched Phase 3 (`gsd-tools list-todos` returned `count: 0`).

</deferred>

---

*Phase: 03-cslc-s1-self-consistency-eu-validation*
*Context gathered: 2026-04-23*
