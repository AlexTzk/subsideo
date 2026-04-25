# Phase 4: DISP-S1 Comparison Adapter + Honest FAIL - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 builds the validation-only `prepare_for_reference` adapter and re-runs the existing DISP pipeline (no algorithmic changes — same dolphin/PHASS/MintPy chain) on the two cached cells:

- **DISP-N.Am.-SoCal** (burst `t144_308029_iw1`, 15 epochs Jan–Jun 2024 — same window Phase 3 CSLC self-consistency calibrated against): re-run from cached CSLCs, separate product-quality (self-consistency) from reference-agreement (r vs OPERA DISP-S1 at 30 m).
- **DISP-EU-Bologna** (burst `t117_249422_iw2`, 19 epochs Jan–Jun 2021 — fully POEORB-era cross-constellation S1A+S1B stack): re-run from cached CSLCs, separate product-quality from reference-agreement (r vs EGMS L2a PS at point coordinates on relative orbit 117).

Plus three artefact deliverables:

- **`prepare_for_reference(native_velocity, reference_grid, method=...)`** in `compare_disp.py` — explicit `method=` argument (no default), accepts (a) GeoTIFF path, (b) `xr.DataArray` with CRS, (c) `ReferenceGridSpec` for EGMS L2a point-sampling — never writes back to the product.
- **Ramp-attribution diagnostic**: per-IFG planar-ramp fit + direction-stability + magnitude-vs-coherence Pearson — splits "PHASS FAIL" into PHASS / orbit / tropospheric / mixed / inconclusive labels in metrics.json + CONCLUSIONS narrative. Two more diagnostics from PITFALLS P3.2 (POEORB swap, ERA5 toggle) are documented as available-but-deferred (current windows are all-POEORB; ERA5 not currently configured).
- **DISP Unwrapper Selection scoping brief**: `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` — one page, 4 candidate approaches × (description, success criterion, compute tier, dep delta) — handoff to the spun-off follow-up milestone.
- **`docs/validation_methodology.md` §3 append** (Phase 3 D-15 append-only policy): DISP ramp-attribution methodology sub-section + multilook method ADR (PITFALLS P3.1 vs FEATURES anti-feature dialogue resolved as `block_mean`).

**Not this phase:**
- Picking a production unwrapper — explicit anti-feature; the brief is the handoff to the dedicated follow-up milestone.
- Modifying the dolphin/PHASS/MintPy pipeline — re-runs use cached CSLCs and the existing `run_disp()` entry point unchanged.
- Tightening `disp.selfconsistency.coherence_min=0.7` or `residual_mm_yr_max=5` based on per-AOI scores (M1 target-creep; CALIBRATING per Phase 1 D-04 with `binding_after_milestone='v1.2'`).
- Tightening reference-agreement `disp.correlation_min=0.92` or `disp.bias_mm_yr_max=3` based on the FAIL numbers we're about to report (M1 target-creep; the FAIL is the intended signal).
- ERA5 tropospheric correction integration — explicitly deferred as DISP-V2-02 (folded into Unwrapper Selection follow-up milestone as secondary).
- Adding new criteria entries — Phase 1 D-04 already shipped `disp.selfconsistency.coherence_min/residual_mm_yr_max` (CALIBRATING) + `disp.correlation_min/bias_mm_yr_max` (BINDING).
- Picking specific candidate threshold values for the brief — the brief proposes success criteria; the follow-up milestone commits.

Phase 4 covers the 5 requirements mapped to it: **DISP-01** (`prepare_for_reference` adapter signature + 3-form reference_grid), **DISP-02** (self-consistency at native 5×10 m for both cells), **DISP-03** (separate product-quality + reference-agreement reporting + ramp-attribution diagnostic), **DISP-04** (DISP Unwrapper Selection brief), **DISP-05** (native 5×10 m stays production default).

</domain>

<decisions>
## Implementation Decisions

### Multilook method ADR (DISP-01, DISP-05, PITFALLS P3.1, FEATURES anti-feature table — the explicitly-flagged Phase 4 ADR)

- **D-01: `prepare_for_reference(..., method=...)` accepts `Literal["gaussian", "block_mean", "bilinear", "nearest"]`.** Captures the four meaningful kernels: PITFALLS-physics (Gaussian σ=0.5×ref), FEATURES-conservative (block-mean averaging), v1.0 ad-hoc (`Resampling.bilinear` from `compare_disp.py:145` and `run_eval_disp.py` Stage 9 — preserved for continuity), and degenerate (`nearest` — included for kernel-comparison studies in the Unwrapper Selection follow-up). Adapter validates `method` against the Literal at call time; refuses `None`/missing per DISP-01 explicit-no-default. No default value at signature level.

- **D-02: Phase 4 eval scripts pass `method="block_mean"` explicitly.** Conservative — matches what OPERA itself uses in its CSLC multilook step; never inflates r through kernel artefact. PITFALLS P3.1 argues Gaussian is physically apples-to-apples (OPERA's 30 m output is itself implicitly Gaussian-smoothed); FEATURES anti-feature table argues the reverse. The ADR resolution is to pick the kernel choice that minimises "we picked the kernel that flattered the metric" attack surface. block_mean is the floor — anyone arguing Gaussian gives higher r can rerun with `method="gaussian"`; we don't pre-commit to the optimistic kernel for the official metric. No goalpost-moving (M1) and no kernel-driven r inflation (FEATURES). The eval-script default DOES NOT bind the adapter default — adapter still requires explicit `method=` per DISP-01.

- **D-03: `docs/validation_methodology.md` §3 contains the ADR sub-section "DISP comparison-adapter design — multilook method choice".** Per Phase 3 D-15 append-only doc policy (Phase 4 owns §3 DISP ramp-attribution + multilook ADR; §4/§5 deferred to Phases 5-7). §3 structure: (1) Problem statement (5×10 m → 30 m or PS-point-sampling required for reference comparison; method choice changes reported r/bias), (2) PITFALLS P3.1 argument (Gaussian σ=0.5×ref physically consistent with OPERA's smoothing), (3) FEATURES anti-feature argument (block_mean conservative, matches OPERA multilook, doesn't inflate r), (4) Decision: block_mean as eval-script default per criterion-immutability principle (kernel choice is a comparison-method decision, NOT a product-quality decision), (5) Constraint: kernel must NOT be tuned to the resulting r/bias number; switching kernels post-measurement requires CONCLUSIONS-level documentation. §3 is appended as ONE PR alongside CONCLUSIONS updates (mirroring Phase 3 D-15 single-section-per-phase append).

- **D-04: Module-level constant + adapter raise-on-missing.** Each eval script declares `REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"` at module top (mirrors Phase 1 D-11 `EXPECTED_WALL_S` constant pattern — auditable in git diff, supervisor AST-parsing not required). Adapter raises `ValueError` if `method` is `None` or missing kw-only. Switching kernels requires editing the constant in the script (visible PR), not setting an env var or CLI flag.

### DISP self-consistency methodology source (DISP-02, FEATURES line 72, Phase 3 D-modules)

- **D-05: Mixed source — coherence from cached CSLC stack, residual from dolphin's velocity output.** Coherence stat: `coherence_stats(ifgrams_stack, stable_mask)` from `selfconsistency.py` (Phase 1 D-module) computed on the cached CSLC stack via the same sequential 12-day IFG approach Phase 3 used (boxcar 5×5 — see D-07). Gate stat = `median_of_persistent` (Phase 3 D-01, locked in `criteria.py` `gate_metric_key` default). Residual stat: `residual_mean_velocity(velocity_mm_yr, stable_mask, frame_anchor='median')` applied to dolphin's `velocity.tif` raster (the unwrapped+inverted output of the dolphin pipeline), NOT to the linear-fit-from-CSLC-stack velocity Phase 3 used. This captures BOTH input-side quality (coherence — should pass) and output-side quality (residual — will FAIL because of PHASS-induced ramps) — the FAIL on residual IS the intended signal that fuels the Unwrapper Selection brief. Reading dolphin's velocity raster + applying the existing helper is ~10 lines of glue code in the eval script; no new module helpers required.

- **D-06: Stable mask = same builder + same parameters as Phase 3 SoCal.** `build_stable_mask(worldcover, slope_deg, coastline, waterbodies, coast_buffer_m=5000, water_buffer_m=500, slope_max_deg=10)` — identical signature to Phase 3 D-09 SoCal mask. SoCal mask reused via cross-cell read (D-08); Bologna mask computed fresh from same builder with Bologna burst bbox (Phase 3 ran Iberian Meseta, not Bologna — no cache to reuse for EU). PITFALLS P2.1 mask-contamination mitigation already in place; no per-AOI tuning (target-creep prevention).

- **D-07: Coherence input = sequential 12-day IFGs from CSLC stack via boxcar 5×5.** Same convention as Phase 3 D-Claude's-Discretion (typical Sentinel-1; hardcoded `boxcar_px=5`). For SoCal: 14 IFGs from the 15-epoch stack already cached. For Bologna: 18 IFGs from the 19-epoch S1A+S1B cross-constellation stack (Bologna 2021 Jan–Jun is dual-sat era; cadence is effectively 6-day, but sequential 12-day pairs still constructed for coherence-stack consistency with SoCal). Numbers are directly comparable across CSLC-self-consist and DISP-self-consist matrix cells — same methodology, same gate stat, same parameters. NOT dolphin's internal coherence layer (would couple validation to product per FEATURES anti-feature framing).

- **D-08: SoCal coherence sub-result reused via cross-cell read; residual fresh from dolphin output.** `eval-disp/metrics.json` `product_quality.coherence` field reads from `eval-cslc-selfconsist-nam/metrics.json` (Phase 3 cell — already produced, identical CSLC stack input, locked at SoCal coh_med_of_persistent=0.887). Provenance flag in DISP-N.Am. metrics.json: `product_quality.coherence_source: 'phase3-cached'` (Literal value enabling matrix-writer audit). Residual is always fresh per-cell from dolphin's `velocity.tif`. Saves ~12 min coherence re-compute on a cold N.Am. run; warm re-run is unaffected. Bologna has no Phase 3 cache (Phase 3 EU was Iberian Meseta, not Bologna) — Bologna gets fresh coherence + fresh residual; provenance flag = `'fresh'`.

### Ramp-attribution diagnostic (DISP-03, PITFALLS P3.2)

- **D-09: Diagnostic (a) per-IFG ramp fit always-on; (b) POEORB swap + (c) ERA5 toggle deferred.** Diagnostic (a) — per-IFG planar-ramp fit + direction-stability + magnitude-vs-coherence — runs every `make eval-disp-{nam,eu}` invocation; cheap (~5 s for 14–18 IFGs via numpy `polyfit`). Diagnostic (b) POEORB swap on RESORB epochs documented as no-op-on-current-stacks: SoCal Phase 3 window is POEORB-only by D-Claude's-Discretion; Bologna 2021 Jan–Jun is fully POEORB-era — neither cell has RESORB epochs to swap. Diagnostic (c) ERA5 toggle requires `pyaps3 >= 0.3.6` + valid `~/.cdsapirc` (CDS API key — not currently configured per CLAUDE.md); ERA5 not enabled in current pipeline. Both (b) and (c) are documented in CONCLUSIONS sections as "diagnostic available; not run because [no RESORB epochs / ERA5 not configured]" — not silently absent. Brief cites diagnostic (a) findings; (b)+(c) explicitly deferred to follow-up milestone or v2 (DISP-V2-02 ERA5 already in REQUIREMENTS).

- **D-10: Ramp-fit code = new helper `fit_planar_ramp(ifgrams_stack, mask)` in `selfconsistency.py`.** Pure-function module additive extension (Phase 1 D-module charter broadens from "Sequential-IFG coherence + reference-frame residual" to "Sequential-IFG self-consistency primitives"). Signature: `fit_planar_ramp(ifgrams_stack: np.ndarray, mask: np.ndarray) -> dict[str, np.ndarray]` returning `{ramp_magnitude_rad: (N,), ramp_direction_deg: (N,), slope_x: (N,), slope_y: (N,), intercept_rad: (N,)}` per IFG (N = stack length). Plan-phase decides whether to additionally return per-IFG ramp-removed residual rasters (probably no — disk footprint would be 14–18 × full-resolution rasters per cell; v2 scope per D-11 schema). Lazy-imports nothing; uses numpy least-squares only.

- **D-11: `metrics.json` ramp_attribution schema = per-IFG list + aggregate + attributed_source label.** Top-level `ramp_attribution: {per_ifg: list[PerIFGRamp], aggregate: {mean_magnitude_rad, direction_stability_sigma_deg, magnitude_vs_coherence_pearson_r, n_ifgs}, attributed_source: Literal['phass', 'orbit', 'tropospheric', 'mixed', 'inconclusive'], attribution_note: str}` field. `PerIFGRamp` shape: `{ifg_idx, ref_date_iso, sec_date_iso, ramp_magnitude_rad, ramp_direction_deg, ifg_coherence_mean}`. CONCLUSIONS table renders the per-IFG list (sortable by `ramp_magnitude_rad` descending so the worst IFGs are visible) + the aggregate row. Matrix cell shows `attributed_source` label. Schema lives as a new Pydantic v2 model in `validation/matrix_schema.py` (extending the existing `MetricsJson` base) — additive, no breaking changes to Phase 1/2/3 cells.

- **D-12: Auto-attribute via rule + human review note in CONCLUSIONS prose.** Eval script writes `attributed_source` per a deterministic rule (plan-phase commits exact thresholds — see Claude's Discretion below): broadly, random direction (σ > some-cutoff) AND magnitude correlates with coherence → 'phass'; stable direction (σ < some-cutoff) → 'orbit'; (c)+(c)-deferred so 'tropospheric' and 'ionospheric' branches are commented as "attribution requires diagnostic (c) which is deferred — flag as 'mixed' if direction stable but no orbit-class explanation". The Literal includes 'inconclusive' and 'mixed' explicitly so the rule never has to lie. CONCLUSIONS prose section "Ramp Attribution" includes a human-review note: "Automated attribution: PHASS. Reviewed: agreed/disagreed/refined to X — [reasoning]." Per Phase 2 D-15 investigation discipline ("automation flags, doesn't replace narrative") the matrix label comes from the auto-attribute (audit trail in metrics.json) but the canonical labelling in the brief comes from the human review.

### Brief + CONCLUSIONS shape (DISP-04, REL-03 trace)

- **D-13: CONCLUSIONS update = append v1.1 sections + rename `CONCLUSIONS_DISP_EGMS.md` → `CONCLUSIONS_DISP_EU.md`.** `git mv CONCLUSIONS_DISP_EGMS.md CONCLUSIONS_DISP_EU.md` to align with `results/matrix_manifest.yml` `disp:eu` cell entry. Both files keep the existing v1.0 narrative as a "v1.0 baseline" leading section (preserves the planar-ramp discovery audit trail — that's WHY we know what to look for). Append four new v1.1 sections to each: (1) **Product Quality** — self-consistency CALIBRATING numbers (coherence + residual, separate sub-section per metric), (2) **Reference Agreement** — block_mean adapter r/bias/RMSE numbers (with the v1.0 ad-hoc-bilinear comparison cited as "for continuity, the v1.0 numbers using `Resampling.bilinear` were r=0.0365 / bias=+23.62 mm/yr (N.Am.) and r=0.32 / bias=+3.35 mm/yr (EU)"), (3) **Ramp Attribution** — per-IFG table + aggregate + auto-attribute label + human review note, (4) **Link to DISP_UNWRAPPER_SELECTION_BRIEF.md**. Mirrors Phase 3 D-08 "two CONCLUSIONS files per cell" pattern; manifest already references `CONCLUSIONS_DISP_N_AM.md` and `CONCLUSIONS_DISP_EU.md`.

- **D-14: Brief cites BOTH v1.1 reference-agreement numbers + ramp-attribution aggregate.** The fresh r/bias/RMSE numbers from `prepare_for_reference(method="block_mean")` are the FAIL state the brief opens with. The ramp-attribution aggregate (mean magnitude rad/IFG, direction-stability σ, automated label) drives candidate prioritisation — if 'phass' label sticks after human review, all four candidates remain viable; if 'orbit' label, candidates 1+2 (PHASS+deramping, SPURT native) become lower-priority since they don't address orbit-state errors; if 'mixed' or 'inconclusive', brief flags need for diagnostics (b)+(c) before candidate evaluation. Brief format per candidate explicitly cites the relevant FAIL number ("PHASS+deramping target: r > 0.5 OR ramp_magnitude_rad < 1.0 — current Bologna r=0.32 / ramp 5.5 rad").

- **D-15: Brief = 4 candidates × (description, success criterion, compute tier, dep delta).** One markdown page (~150–250 LOC). Candidate set per FEATURES + ROADMAP: PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback. Per-candidate columns: (a) description (1–2 sentences on what changes), (b) success criterion (concrete numerical target: r > X, ramp magnitude < Y rad, or bias < Z mm/yr — derived from the FAIL numbers), (c) compute tier (S = post-process only, M = re-unwrap from cached IFGs, L = re-unwrap from cached CSLCs), (d) dep delta (additional packages or config required vs. current pipeline). Markdown table-friendly. Single dense page; not a plan, not an ADR. NO MintPy SBAS as 5th candidate (research's 4-candidate framing intentional; resists scope creep).

- **D-16: Brief lives at `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md`; committed at Phase 4 close.** Co-located with Phase 2's `rtc_eu_burst_candidates.md` and Phase 3's `cslc_selfconsist_aoi_candidates.md` probe artifacts — `v1.1-research/` is the canonical home for forward-looking research artifacts that feed downstream phases or the next milestone. Committed in the final Phase 4 commit alongside CONCLUSIONS updates. Brief author = Claude (research output, not code); user reviews + greenlights before commit (mirrors Phase 2 D-04 "Claude drafts; user reviews" discipline). NOT in `docs/` (audience is research-handoff-internal, not product-facing) and NOT in a v1.2 milestone directory (v1.2 not yet roadmapped).

### Cross-cutting (carry-forwards from earlier phases — listed for traceability, NOT re-decided here)

- **D-17: Native 5×10 m stays production default.** `run_disp()` entry point unchanged; `prepare_for_reference` is validation-only — never writes back to product (DISP-05 + ROADMAP key decision + research ARCHITECTURE §3.1).
- **D-18: `prepare_for_reference` lives in `compare_disp.py`, NOT a new `validation/adapters.py`.** Per research ARCHITECTURE §3 (only DISP needs the adapter in v1.1; speculative generality rejected). Promotion rule: extract to `validation/adapters.py` only when a 2nd product needs the same adapter (earliest: DISP Unwrapper Selection follow-up adds a CSLC-native-resolution gate).
- **D-19: First-rollout = CALIBRATING cell rendering for `disp.selfconsistency.*`.** Phase 3 D-03 cell_status semantics inherited: `Literal['PASS','FAIL','CALIBRATING','MIXED','BLOCKER']`. `disp.selfconsistency.coherence_min` + `residual_mm_yr_max` are CALIBRATING with `binding_after_milestone='v1.2'` (Phase 1 D-04 already shipped); SoCal + Bologna = data points 1 + 2 of the new gate (<3 → CALIBRATING). Reference-agreement `disp.correlation_min`/`bias_mm_yr_max` are BINDING from v1.0 → render PASS/FAIL normally. Cell-level status: MIXED (CALIBRATING product_quality + FAIL reference_agreement is the expected outcome on both cells until unwrapper is fixed in the follow-up milestone).
- **D-20: No pipeline algorithm changes.** Re-runs use cached CSLCs + the existing `run_disp()` chain (dolphin/PHASS/MintPy + ad-hoc tropo-correct-OFF). FEATURES line 73: "~30 min compute from cache" per cell. Phase 4 changes are validation-side only (adapter, ramp-fit, separated metrics, schema additions, doc append). No `products/disp.py` edits.
- **D-21: Manifest already wires the cells.** `disp:nam` → `eval-disp/`, `disp:eu` → `eval-disp_egms/` (Phase 1 D-08). The `cache_dir` for EU stays `eval-disp_egms/` even though the CONCLUSIONS file renames to `_EU.md` (cache dir name is internal; CONCLUSIONS file is user-facing — they don't have to match).

### Claude's Discretion (for plan-phase)

- **`fit_planar_ramp` exact algorithm details** — least-squares plane fit in image coordinates vs UTM coordinates; ramp computed on the masked stable-pixel subset vs full burst (probably full burst for diagnostic purposes — orbit/tropo ramps span the burst, masking to stable-only would clip them); NaN policy for outside-burst-footprint pixels (parallelogram → rectangular padding). Default: full-burst least-squares plane fit on finite-non-zero pixels in image coordinates; report magnitude in rad (peak-to-peak across the burst), direction in degrees from East.
- **Auto-attribute rule thresholds** — `direction_stability_sigma_deg < 30°` → 'orbit'; `magnitude_vs_coherence_pearson_r > 0.5` → 'phass'; both true → 'mixed'; neither → 'inconclusive'. Plan-phase commits the exact cutoffs based on what the diagnostic-(a) numbers actually look like on SoCal + Bologna; if the rule misclassifies a clear visual case, plan-phase tunes once and locks. Cutoffs are NOT criteria.py entries (rule is for narrative attribution, not gating).
- **EXPECTED_WALL_S for the supervisor** — DISP re-run from cache + ramp-fit + adapter compute: ~30 min/cell warm; cold (full pipeline from CSLCs) ~3 hours/cell. Supervisor budget: cap at 6 hours per cell-script with a per-cell budget guard (matches Phase 3 D-Claude's-Discretion). If first run blows past 6 hours, plan-phase decides whether to raise or to fail-loudly.
- **`DISPCellMetrics` Pydantic v2 schema shape** — extends `MetricsJson` base, adds `product_quality: ProductQualityResult` (coherence sub-result with `coherence_source: Literal['phase3-cached','fresh']` provenance + residual sub-result) + `reference_agreement: ReferenceAgreementResult` (r, bias, rmse, sample_count) + `ramp_attribution: RampAttribution` (D-11). One Pydantic class for both DISP cells (no per-region subtype needed; Bologna and SoCal share schema even with different reference data sources).
- **Bologna stable-mask data sources** — Phase 3 SoCal used Natural Earth coastlines + WorldCover class 60 (Phase 3 D-Claude's-Discretion). Bologna is inland Po-plain — coastline buffer is ~100 km from burst, so coast buffer is irrelevant; water-body buffer applies (Po river + reservoirs). Plan-phase confirms Natural Earth + WorldCover suffice for Bologna; revisits to OSM if buffer exclusion is too coarse/fine.
- **Whether to render the `bilinear` v1.0 numbers in CONCLUSIONS for continuity** — D-13 states "v1.0 numbers cited" but the exact framing (separate "v1.0 baseline (Resampling.bilinear)" sub-section vs inline footnote) is plan-phase prose decision.
- **Brief publication date stamp** — committed at Phase 4 close; the brief's introductory paragraph notes "as of `<date>`, current FAIL state is..." for future readers.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source-of-truth scope (read first)

- `.planning/ROADMAP.md` §Phase 4 (lines 129–145) — goal, 4 success criteria, 5 requirements (DISP-01..05), planning-artifact flag on multilook method default ADR.
- `.planning/REQUIREMENTS.md` §DISP-01..05 (lines for "DISP-S1 Comparison Adapter + Honest FAIL") — full text of the 5 requirements, plus DISP-V2-01/02/03 future work for context.
- `.planning/PROJECT.md` — pass criteria (DISP r > 0.92, bias < 3 mm/yr); v1.1 metrics-vs-targets discipline paragraph; key decision "Native CSLC/DISP resolution stays production default; downsampling only in comparison adapter"; key decision "Spin DISP unwrapper selection out to a dedicated follow-up milestone".
- `.planning/STATE.md` — v1.1 accumulated decisions; Phase 3 closed status; Phase 4 multilook method ADR flagged in Blockers/Concerns.

### Phase 1/2/3 CONTEXT (REQUIRED for understanding harness, criteria, schema, append-only doc policy)

- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-CONTEXT.md` — D-01..D-19: criteria.py shape (frozen-dataclass + Literal['BINDING','CALIBRATING','INVESTIGATION_TRIGGER'] + `binding_after_milestone` + `gate_metric_key`); split `ProductQualityResult` / `ReferenceAgreementResult` (D-06, D-08); shared `selfconsistency.py` + `stable_terrain.py` D-modules (D-04 — Phase 4 is 2nd consumer after Phase 3); supervisor mechanics (D-10..D-14); harness 5 helpers (D-Claude's-Discretion).
- `.planning/phases/02-rtc-s1-eu-validation/02-CONTEXT.md` — D-05 declarative AOIS-list pattern; D-06 per-AOI try/except; D-09..D-12 metrics.json + meta.json shape + matrix row format; D-13..D-15 INVESTIGATION_TRIGGER discipline (Phase 4 borrows the "automation flags, doesn't replace narrative" framing for ramp-attribution).
- `.planning/phases/03-cslc-s1-self-consistency-eu-validation/03-CONTEXT.md` — D-01 `median_of_persistent` gate stat (locked in `criteria.py`); D-03 first-rollout CALIBRATING cell rendering; D-08 two CONCLUSIONS files per cell; D-13/D-14/D-15 `docs/validation_methodology.md` append-only by phase (Phase 4 owns §3 DISP ramp-attribution + multilook ADR; do NOT add §4/§5).
- `.planning/phases/03-.../03-05-SUMMARY.md` — confirms `docs/validation_methodology.md` §1 + §2 landed; Phase 4 appends §3 in single PR.

### Phase 4 research (authoritative for HOW)

- `.planning/research/SUMMARY.md` (lines 168–172) — Phase 4 row: scope contracted; deliverables (`prepare_for_reference` + self-consistency gate + ramp-attribution + brief); watch-out P3.1 (multilook method tension), P3.2 (ramp-attribution mandatory before "PHASS FAIL" label), M2 (separate gates).
- `.planning/research/SUMMARY.md` (lines 100–110, 220–230) — Research Flag: multilook method default explicitly named as Phase 4 ADR; PITFALLS-vs-FEATURES tension. Resolution = D-02 block_mean + D-03 ADR doc-section.
- `.planning/research/PITFALLS.md` §P3.1 (lines 391–417) — multilook method physics argument: Gaussian σ=0.5×ref consistent with OPERA's smoothing; explicit `method=` no default; grid-snap to reference origin secondary; warning signs (velocity-histogram-width inflation as kernel-induced artefact).
- `.planning/research/PITFALLS.md` §P3.2 (lines 422–448) — ramp-attribution diagnostic: 4 ramp sources (PHASS / tropospheric / orbit / ionospheric); 3 diagnostic tests (per-IFG ramp-fit + direction-stability + magnitude-vs-coherence; POEORB swap; ERA5 toggle); attribution table; "do not label PHASS without diagnostic" policy. D-09..D-12 follow this directly.
- `.planning/research/FEATURES.md` (lines 67–76) — Phase 3-in-research-numbering table-stakes: `prepare_for_reference` signature + 3-form `reference_grid` argument + `compare_disp.py` placement + "Never writes back to the product"; DISP self-consistency gate "same methodology as Phase 2 CSLC" + "Inputs: cached CSLC stack; Outputs: coherence + residual"; N.Am.+EU re-runs ~30 min from cache; Brief at `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` (1 page, 4 candidates, success criterion + compute tier each); CONCLUSIONS update (separate product_quality + reference_agreement).
- `.planning/research/FEATURES.md` §anti-features (lines 142–143) — multilook method anti-feature framing (Gaussian/Lanczos = inflate r through kernel; block_mean conservative); "writing comparison-adapter output back to the product" anti-feature.
- `.planning/research/ARCHITECTURE.md` §3 (lines 133–158) — `prepare_for_reference()` placement in `compare_disp.py` rationale (NOT `validation/adapters.py`); module docstring update; signature with `reference_grid: Path | xr.DataArray | ReferenceGridSpec` 3-form union.
- `.planning/research/ARCHITECTURE.md` §1 — harness public API (Phase 4 reuses `bounds_for_burst`, `select_opera_frame_by_utc_hour`, `download_reference_with_retry`, `ensure_resume_safe`, `credential_preflight`, `find_cached_safe`).
- `.planning/research/STACK.md` — pyaps3 >= 0.3.6 only if ERA5 toggle (deferred per D-09); rio-cogeo 6.0.0 via `_cog.py`; tophu/snaphu via conda-forge (no Phase 4 changes — pipeline unchanged per D-20).

### v1.0 CONCLUSIONS (context for the FAIL state Phase 4 inherits)

- `CONCLUSIONS_DISP_N_AM.md` (258 LOC, 2026-04-13) — SoCal r=0.0365 / bias=+23.62 mm/yr / FAIL; §5.1 PHASS planar-ramp discovery (every IFG flagged with residual-RMS 3–14 rad vs 1.0 rad threshold); §5.2 attempted SNAPHU+tophu fallback that hung; §6.5 "PHASS introduces planar ramps that propagate linearly through dolphin's network inversion into the final velocity field". Phase 4 D-13 keeps this section as "v1.0 baseline" preamble.
- `CONCLUSIONS_DISP_EGMS.md` (304 LOC, 2026-04-15) — Bologna r=0.32 / bias=+3.35 mm/yr / RMSE 5.14 mm/yr / FAIL; §3 first EU end-to-end run (CDSE STAC 1.1.0 rewrite + S3 dedicated keys + SAFE directory tree download — all reusable); §4.3 same PHASS planar-ramp signature (38 of 38 IFGs flagged); §6 candidate mitigations list (PHASS→SNAPHU+tophu primary; ERA5 secondary; longer stack); §7 final verdict "FAIL on both runs because of single upstream root cause — dolphin's PHASS unwrapper". Renamed to `CONCLUSIONS_DISP_EU.md` per D-13.
- `CONCLUSIONS_CSLC_N_AM.md` §5 (referenced by D-08 + Phase 3 D-13 §1 cross-version impossibility methodology) — context for why CSLC stack quality is high but DISP output isn't.

### v1.0 precedent files to match (existing conventions)

- `src/subsideo/validation/compare_disp.py` (380 LOC) — primary modification surface. `compare_disp()` (Ortho raster) + `compare_disp_egms_l2a()` (PS points) + `_load_egms_l2a_points()` helper exist; both currently use `Resampling.bilinear` (line 145 of `compare_disp`). Phase 4 ADDS `prepare_for_reference()` as a top-level function; `compare_disp()` and `compare_disp_egms_l2a()` MAY internally call `prepare_for_reference()` (refactor opportunity per ARCHITECTURE §3 — replaces ad-hoc bilinear with the new adapter; plan-phase decides scope of refactor).
- `src/subsideo/validation/selfconsistency.py` (327 LOC, post-Phase-3) — `coherence_stats` (6 stats incl. `median_of_persistent`), `residual_mean_velocity` (frame-anchor='median' default), `compute_residual_velocity` (Phase 3-landed linear-fit helper). Phase 4 ADDS `fit_planar_ramp(ifgrams_stack, mask)` per D-10 — pure-function additive extension; module charter broadens to "Sequential-IFG self-consistency primitives".
- `src/subsideo/validation/stable_terrain.py` (208 LOC, Phase 1) — `build_stable_mask` consumed unchanged for both cells per D-06.
- `src/subsideo/validation/criteria.py` (Phase 1) — `disp.correlation_min=0.92`, `disp.bias_mm_yr_max=3.0` (BINDING), `disp.selfconsistency.coherence_min=0.7`, `disp.selfconsistency.residual_mm_yr_max=5.0` (CALIBRATING with `binding_after_milestone='v1.2'`, `gate_metric_key='median_of_persistent'`) all already shipped — Phase 4 makes ZERO criteria.py edits.
- `src/subsideo/validation/matrix_schema.py` — Pydantic v2 base. Phase 4 ADDS `DISPCellMetrics` (extends `MetricsJson`) + `RampAttribution` model + `PerIFGRamp` model. No edits to existing types (Phase 1 D-09 big-bang migration locked the schema; Phase 4 is additive).
- `src/subsideo/validation/matrix_writer.py` — Phase 4 adds render branch for `disp:nam` + `disp:eu` cell types (italicised CALIBRATING for product-quality + PASS/FAIL for reference-agreement + attributed_source label inline).
- `src/subsideo/validation/harness.py` — 5 helpers consumed unchanged; Phase 4 is the ~5th harness consumer (after Phase 1 pilot + Phase 2 RTC-EU + Phase 3 CSLC-NAM/EU).
- `src/subsideo/validation/supervisor.py` — Phase 4 eval scripts declare `EXPECTED_WALL_S` (Phase 1 D-11 convention; budget per D-Claude's-Discretion above).
- `src/subsideo/products/disp.py` (725 LOC) — `run_disp()` entry point. UNCHANGED in Phase 4 per D-20. `_mp.configure_multiprocessing()` fires once at top per Phase 1 D-14.
- `run_eval_disp.py` (859 LOC) — N.Am. eval, primary modification target. Phase 4 changes: (1) Stage 9 ad-hoc reproject → `prepare_for_reference(method="block_mean")` call; (2) add product-quality computation block (coherence cross-cell read + residual from velocity.tif); (3) add ramp-attribution block (call `fit_planar_ramp` on cached unwrapped IFGs + write `ramp_attribution` field to metrics.json); (4) write nested `metrics.json` per `DISPCellMetrics` schema; (5) declare `REFERENCE_MULTILOOK_METHOD = "block_mean"` constant + `EXPECTED_WALL_S` per D-04 + D-Claude's-Discretion.
- `run_eval_disp_egms.py` (565 LOC) — EU eval, parallel modification target with same 5 changes as N.Am. (Bologna-specific: no Phase 3 cache reuse — D-08 fresh path).
- `CONCLUSIONS_RTC_EU.md` — template for the multi-section CONCLUSIONS shape Phase 4 emulates (Calibration Framing + Investigation discipline + Attribution table — RTC-EU's investigation table is the analogue of DISP's ramp-attribution table).
- `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (Phase 2) and `cslc_selfconsist_aoi_candidates.md` (Phase 3) — templates for the brief's location convention; brief is research output not eval-script output.
- `results/matrix_manifest.yml` — already lists `disp:nam` + `disp:eu` cells (Phase 1 D-08). Phase 4 fills `eval-disp/metrics.json` + `eval-disp_egms/metrics.json` at runtime; conclusions_doc field gets updated from `CONCLUSIONS_DISP_EGMS.md` → `CONCLUSIONS_DISP_EU.md` in the same commit as the file rename (D-13).
- `Makefile` — `eval-disp-nam` + `eval-disp-eu` targets already exist (line 32–33). Phase 4 fills the referenced scripts.

### External library refs (read as-needed during plan-phase)

- `dolphin` 0.42.5 — `velocity.tif` output schema (units rad/yr per `compare_disp.py` `velocity_units="rad_per_year"` default; converted via `-v_rad * λ / (4π) * 1000` to mm/yr for residual computation per `selfconsistency.compute_residual_velocity` step 5).
- `numpy.linalg.lstsq` / `numpy.polyfit` — least-squares plane fit for `fit_planar_ramp`; pure-numpy, no conda-forge deps.
- `rasterio.warp.Resampling` — `bilinear` and `nearest` mappings for `prepare_for_reference("bilinear", "nearest")` modes; existing dep, no new install.
- `scipy.ndimage.gaussian_filter` (or equivalent) — Gaussian kernel for `prepare_for_reference("gaussian")` mode if plan-phase chooses that branch; scipy is a transitive dep already (rasterio + skimage chain).
- `xarray` + `rioxarray` — for `prepare_for_reference` `xr.DataArray` reference-grid form (DISP-01 form b); already in `pyproject.toml` validation extras.
- `EGMStoolkit` 0.2.15 — unchanged from v1.0; reference data already cached for Bologna.
- `earthaccess` — OPERA DISP-S1 reference fetch for SoCal; already in v1.0 pipeline.

### No external ADR/spec docs for Phase 4

Phase 4 is codebase-internal validation work; no external spec consumed. The multilook method ADR lives in-repo at `docs/validation_methodology.md` §3 (D-03), not a separate ADR doc. Brief lives in `.planning/milestones/v1.1-research/`, also in-repo.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`src/subsideo/validation/compare_disp.py` (380 LOC, post-Phase-1)** — primary surface. `compare_disp(product_path, egms_ortho_path, incidence_angle_path, mean_incidence_deg=33.0)` + `compare_disp_egms_l2a(velocity_path, egms_csv_paths, velocity_col, velocity_units)` + `_load_egms_l2a_points(csv_paths, velocity_col)` + `_los_to_vertical(los_velocity, incidence_angle)`. Both top-level comparison functions emit `DISPValidationResult` with split `product_quality` (currently empty `measurements={}`) + `reference_agreement` (`correlation`, `bias_mm_yr`). Phase 4 ADDS `prepare_for_reference(...)` and FILLS `product_quality.measurements` for the two emit sites.
- **`src/subsideo/validation/selfconsistency.py` (327 LOC, post-Phase-3)** — `coherence_stats(ifgrams_stack, stable_mask)` + `residual_mean_velocity(velocity_mm_yr, stable_mask, frame_anchor='median')` + `compute_residual_velocity(cslc_stack_paths, stable_mask, sensing_dates=None)`. Phase 4 ADDS `fit_planar_ramp(ifgrams_stack, mask)` per D-10. No edits to existing helpers.
- **`src/subsideo/validation/stable_terrain.py` (208 LOC, Phase 1)** — `build_stable_mask` consumed unchanged for both cells.
- **`src/subsideo/validation/criteria.py` (262 LOC, Phase 1+2)** — `disp.*` entries already shipped (D-19 trace). ZERO Phase 4 edits.
- **`src/subsideo/validation/harness.py` (627 LOC, Phase 1)** — 5 helpers; Phase 4 reuses `bounds_for_burst`, `select_opera_frame_by_utc_hour`, `find_cached_safe`, `ensure_resume_safe`, `credential_preflight`, `download_reference_with_retry` per existing eval-script patterns.
- **`src/subsideo/validation/matrix_schema.py` (449 LOC)** — Pydantic v2 base. ADD `DISPCellMetrics` + `RampAttribution` + `PerIFGRamp` (D-11).
- **`src/subsideo/validation/matrix_writer.py` (475 LOC)** — manifest-driven cell renderer. ADD `disp:nam` + `disp:eu` render branches.
- **`src/subsideo/validation/supervisor.py`** — subprocess wrapper. Phase 4 scripts declare `EXPECTED_WALL_S` per Phase 1 D-11.
- **`run_eval_disp.py` (859 LOC)** — N.Am. eval, primary modification target. 9-stage pipeline already in place: auth → OPERA ref search → ASF SAFE search → DEM fetch → burst DB → 15× run_cslc → run_disp → read velocity → Stage 9 ad-hoc reproject + comparison.
- **`run_eval_disp_egms.py` (565 LOC)** — EU eval, parallel modification target.
- **`CONCLUSIONS_DISP_N_AM.md` (258 LOC) + `CONCLUSIONS_DISP_EGMS.md` (304 LOC)** — v1.0 narratives kept as "v1.0 baseline" preamble (D-13).
- **`docs/validation_methodology.md` (existing from Phase 3)** — append §3 (D-03) per Phase 3 D-15 single-PR-per-phase append discipline.

### Established Patterns

- **Lazy imports for conda-forge deps** — Phase 4 new code (`fit_planar_ramp`, `prepare_for_reference`) imports xarray/rioxarray/rasterio inside function bodies, not at module top (Phase 1 lazy-import discipline).
- **`if __name__ == "__main__":` guard + `credential_preflight` first + harness consumption** — Phase 4 eval scripts already match this shape; only stage-internal additions.
- **Per-stage `ensure_resume_safe` gate** — Phase 4 re-runs with cached CSLCs are warm by definition; per-stage gates skip stages that already completed.
- **Declarative module-level constants** — `EXPECTED_WALL_S` (Phase 1 D-11) + `REFERENCE_MULTILOOK_METHOD` (Phase 4 D-04) at module top; auditable in git.
- **Aggregate metrics.json + nested sub-results** — Phase 2 D-09/D-10, Phase 3 D-06 pattern. Phase 4 adds `ramp_attribution` as a 3rd top-level sub-aggregate alongside `product_quality` + `reference_agreement`.
- **Cell-level meta.json with input hashes** — Phase 2 D-12. Phase 4 nested per-input-source hashes (CSLC stack hash, OPERA DISP-S1 reference hashes, EGMS L2a CSV hashes, dolphin velocity.tif hash, dolphin internal-coherence-layer hash if read).
- **Matrix-writer manifest-authoritative** — never globs CONCLUSIONS_*.md; reads from `metrics.json` only via `matrix_manifest.yml`.
- **CALIBRATING italicisation in matrix cell** — Phase 1 D-03 + Phase 3 D-03 inherited; matrix_writer renders DISP cells with mixed PASS/FAIL (reference-agreement) + CALIBRATING (product-quality) per D-19.
- **Loguru + pydantic-settings + hatchling** — unchanged.
- **Two CONCLUSIONS files per cell (Phase 3 D-08)** — Phase 4 keeps two: `CONCLUSIONS_DISP_N_AM.md` + `CONCLUSIONS_DISP_EU.md` (post-rename per D-13).
- **`docs/validation_methodology.md` append-only by phase (Phase 3 D-15)** — Phase 4 owns §3 only.

### Integration Points

- **`src/subsideo/validation/compare_disp.py`** — additive: new top-level `prepare_for_reference(native_velocity, reference_grid, *, method)` per DISP-01 signature + D-01 method Literal + D-04 raise-on-missing. Optional refactor: `compare_disp()` Step 2 + `run_eval_disp.py` Stage 9 ad-hoc bilinear → call `prepare_for_reference(method="block_mean")` (plan-phase decides scope).
- **`src/subsideo/validation/selfconsistency.py`** — additive: new `fit_planar_ramp(ifgrams_stack, mask)` per D-10. No edits to existing helpers.
- **`src/subsideo/validation/matrix_schema.py`** — additive new Pydantic types: `DISPCellMetrics`, `RampAttribution`, `PerIFGRamp` per D-11. No edits to existing types.
- **`src/subsideo/validation/matrix_writer.py`** — additive new render branches for `disp:nam` + `disp:eu` cell types.
- **`Makefile`** — unchanged (targets exist).
- **`results/matrix_manifest.yml`** — single-line edit: `disp:eu` `conclusions_doc: CONCLUSIONS_DISP_EU.md` (was `CONCLUSIONS_DISP_EU.md` already in current state per code scout — confirm in plan-phase; rename of file is the actual change).
- **`.gitignore`** — existing `eval-*/` rule auto-ignores cache dirs.
- **New files**:
  - `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` (post-eval).
  - `docs/validation_methodology.md` §3 append (Phase 3 D-15 single-PR-per-phase).
- **Renamed file**:
  - `CONCLUSIONS_DISP_EGMS.md` → `CONCLUSIONS_DISP_EU.md` (D-13 git mv).
- **Modified files**:
  - `run_eval_disp.py` + `run_eval_disp_egms.py` (5 changes per D-Claude's-Discretion: adapter call, product-quality block, ramp-attribution block, metrics.json schema upgrade, REFERENCE_MULTILOOK_METHOD constant).
  - `src/subsideo/validation/compare_disp.py` (add `prepare_for_reference`).
  - `src/subsideo/validation/selfconsistency.py` (add `fit_planar_ramp`).
  - `src/subsideo/validation/matrix_schema.py` (add 3 Pydantic types).
  - `src/subsideo/validation/matrix_writer.py` (add 2 cell render branches).
  - `CONCLUSIONS_DISP_N_AM.md` + `CONCLUSIONS_DISP_EU.md` (append v1.1 sections per D-13).
  - `docs/validation_methodology.md` (append §3 per D-03).

### Script / Cell Flow (data shape)

```
run_eval_disp.py / run_eval_disp_egms.py:
  EXPECTED_WALL_S = 21600  # 6 hours per D-Claude's-Discretion
  REFERENCE_MULTILOOK_METHOD = "block_mean"  # D-04

  # Stages 1-7 unchanged (auth, OPERA ref search, ASF SAFE search, DEM/orbit/burst-DB,
  #                       run_cslc x N (cached), run_disp (cached))
  # Stage 8 unchanged (read velocity raster from dolphin output)

  # Stage 9 (refactored):
  #   (A) Reference-agreement (block_mean adapter)
  velocity_on_ref = prepare_for_reference(velocity_path, reference_grid, method=REFERENCE_MULTILOOK_METHOD)
  ra = compare_disp(...)  # OR compare_disp_egms_l2a(...) — refactored to consume velocity_on_ref

  # Stage 10 (NEW — product-quality block):
  stable_mask = build_stable_mask(worldcover, slope, coastline, waterbodies,
                                   coast_buffer_m=5000, water_buffer_m=500)
  if cell == "disp:nam" and Path("eval-cslc-selfconsist-nam/metrics.json").exists():
    coh_stats = json_load("eval-cslc-selfconsist-nam/metrics.json")["product_quality"]["coherence"]
    coherence_source = "phase3-cached"
  else:
    ifgrams = compute_ifg_coherence_stack(cslc_paths, boxcar_px=5)  # 14 or 18 IFGs
    coh_stats = coherence_stats(ifgrams, stable_mask)  # 6 stats including median_of_persistent
    coherence_source = "fresh"
  velocity_mm_yr = read_dolphin_velocity_tif(velocity_path)  # convert rad/yr → mm/yr if needed
  residual = residual_mean_velocity(velocity_mm_yr, stable_mask, frame_anchor='median')
  pq = ProductQualityResult(
    measurements={"coherence_median_of_persistent": coh_stats["median_of_persistent"],
                  "residual_mm_yr": residual,
                  "coherence_source": coherence_source,
                  # diagnostics
                  ...other 4 coherence stats},
    criterion_ids=["disp.selfconsistency.coherence_min", "disp.selfconsistency.residual_mm_yr_max"],
  )

  # Stage 11 (NEW — ramp-attribution block):
  unwrapped_ifgrams_stack = read_dolphin_unwrapped_ifgs(disp_dir)  # (N, H, W) rad
  ramp_data = fit_planar_ramp(unwrapped_ifgrams_stack, mask=full_burst_finite_mask)
  ramp_aggregate = compute_ramp_aggregate(ramp_data, ifg_coherence_per_ifg=...)
  attributed_source = auto_attribute_ramp(ramp_aggregate)  # rule per D-12 plan-phase thresholds
  ramp_attribution = RampAttribution(
    per_ifg=[PerIFGRamp(...) for ramp in ramp_data],
    aggregate=ramp_aggregate,
    attributed_source=attributed_source,
    attribution_note="Automated; human review pending in CONCLUSIONS",
  )

  # Stage 12 (NEW — write):
  cell_metrics = DISPCellMetrics(
    schema_version=1,
    product_quality=pq,
    reference_agreement=ra.reference_agreement,
    ramp_attribution=ramp_attribution,
    cell_status=infer_cell_status(...),  # MIXED expected
  )
  write eval-disp/metrics.json (or eval-disp_egms/metrics.json)
  write eval-disp/meta.json (or eval-disp_egms/meta.json) with input hashes
```

</code_context>

<specifics>
## Specific Ideas

- **The FAIL on residual IS the intended Phase 4 signal.** v1.0 already proved the pipeline works structurally (CONCLUSIONS_DISP_N_AM.md §6.5, CONCLUSIONS_DISP_EGMS.md §7). Phase 4 isn't trying to fix the FAIL — it's trying to (a) characterise it cleanly with the new adapter so the brief has clean numbers, and (b) attribute the ramp diagnostically so the follow-up milestone scopes to the right candidate. Producing CALIBRATING product-quality + FAIL reference-agreement on both cells is the success outcome.
- **block_mean over Gaussian is a posture, not a science argument.** PITFALLS P3.1's physics argument is correct in isolation (OPERA's 30 m output is Gaussian-smoothed; matching σ would be apples-to-apples). FEATURES anti-feature framing wins because we're a milestone-publish artifact, not a paper — the kernel choice that gives the lower-bound r is the one we ship as the official number, and the ADR doc-section names this trade-off explicitly. If the follow-up milestone wants Gaussian for its own validation, `prepare_for_reference(method="gaussian")` is one keyword change.
- **Phase 3 SoCal cache reuse is a coherence-only optimization, not a "Phase 4 doesn't run on N.Am." shortcut.** D-08 is explicit: residual ALWAYS comes from dolphin's velocity output (which is what we're validating); only the coherence sub-result reads cross-cell. Provenance flag in metrics.json makes the optimization auditable.
- **Bologna 2021 is fully POEORB-era; Phase 3 SoCal window was POEORB-only by D-Claude's-Discretion.** D-09 deferral of diagnostic (b) POEORB swap is a no-op-on-current-stacks; not a methodological gap. If the follow-up milestone runs on a window with RESORB epochs (e.g. winter 2024 SoCal where POEORB delays may force RESORB), diagnostic (b) becomes immediately actionable.
- **ERA5 toggle (diagnostic c) deferred is not a methodological gap.** Per CONCLUSIONS_DISP_EGMS.md §6 candidate-mitigations, ERA5 reduces large-scale phase curvature but not per-IFG ramps directly. The milestone's claim that diagnostic (c) is required to label "tropospheric" is correct, but Phase 4's purpose is to produce honest FAIL numbers + attribution — labelling 'tropospheric' confidently requires (c), so Phase 4's auto-attribute rule outputs 'inconclusive' or 'mixed' if the (a) signature suggests tropospheric without (c) confirmation. Brief flags this need explicitly.
- **The brief's audience is a future contributor with the v1.1 closure in hand.** Brief structure prioritises numbers + per-candidate concrete success criteria over explanation. Anyone wanting the explanation reads CONCLUSIONS first; the brief is the action handoff.
- **The §3 multilook ADR doc-section is the single PR-mergeable artifact closing the v1.1 ADR queue.** Phase 3 §1 + §2 landed; Phase 4 §3 closes the methodology-doc-from-Phase-3-onward planning queue. Phases 5-7 add §4-§5 per their own evidence per D-15 append-only policy.

</specifics>

<deferred>
## Deferred Ideas

- **ERA5 tropospheric correction integration** — DISP-V2-02 already in REQUIREMENTS as future work; folded into Unwrapper Selection follow-up milestone as secondary per Phase 4 D-09 + per CONCLUSIONS_DISP_EGMS §6. Phase 4 documents diagnostic (c) as "available; deferred"; not a methodological gap.
- **POEORB swap automation when RESORB epochs are present** — D-09 + D-Claude's-Discretion: opportunistic-only if RESORB detected. Current windows are all-POEORB → deferred; the auto-detect branch could be added when the first RESORB-containing window appears.
- **Gaussian-kernel re-run for kernel-comparison study** — `prepare_for_reference(method="gaussian")` is one keyword change; running it for comparison is follow-up-milestone scope. CONCLUSIONS may cite "block_mean reference shows r=X; the same data with method='gaussian' would yield r=Y" as a v1.2/v2 footnote. Not Phase 4.
- **Promotion of `prepare_for_reference` to `validation/adapters.py`** — D-18 promotion rule: only when a 2nd product needs it (earliest: DISP Unwrapper Selection follow-up adds CSLC-native-resolution gate). Premature now.
- **`fit_planar_ramp` with per-IFG residual rasters returned** — D-10 schema decision: just per-IFG ramp parameters, not residual rasters. Disk footprint reasoning. v2 if a downstream tool wants the residual rasters.
- **DISP self-consistency on dolphin's coherence layer (input + output coupling)** — Q3-rejected option in discuss; FEATURES anti-feature framing. Reusing dolphin's coherence-shrinkage output to validate dolphin's velocity output couples validation to product. Phase 4 sticks with sequential 12-day IFGs from CSLC stack.
- **MintPy SBAS as 5th brief candidate** — D-15-rejected. Research's 4-candidate framing is intentional; resists scope creep. Could be added in the follow-up milestone if PHASS+deramping/SPURT/tophu-SNAPHU/20×20m-fallback all FAIL their per-candidate success criteria.
- **Full ADR sub-document at docs/adr/004-multilook-method.md** — D-03-rejected. Single ADR sub-section in `docs/validation_methodology.md` §3. ADR-tree rot prevention.
- **Brief stored in v1.2-disp-unwrapper-selection/ milestone directory** — D-16-rejected (v1.2 not yet roadmapped). Brief lives in `v1.1-research/`; the follow-up milestone roadmapper consumes it as input when v1.2 (or whichever version) starts.
- **Per-cell `EXPECTED_WALL_S` budget tuning** — D-Claude's-Discretion: 6h cap as starting point. Refine in plan-phase if observed wall times warrant.
- **Bologna stable-mask via OSM coastlines** — D-Claude's-Discretion: Natural Earth default; revisit to OSM if buffer exclusion is insufficient on Bologna (unlikely — burst is inland Po-plain, coastline buffer is near-irrelevant).
- **v1.0 numbers continuity rendering style** — D-Claude's-Discretion plan-phase prose decision: separate "v1.0 baseline (Resampling.bilinear)" sub-section vs inline footnote in CONCLUSIONS.
- **Render the v1.0 numbers in the brief's opening paragraph for orientation** — possibly. Plan-phase decides; default = brief opens with v1.1 numbers, treats v1.0 as historical and references CONCLUSIONS for the audit trail.

### Reviewed Todos (not folded)

No pending todos matched Phase 4 (`gsd-tools list-todos` returned `count: 0`).

</deferred>

---

*Phase: 04-disp-s1-comparison-adapter-honest-fail*
*Context gathered: 2026-04-25*
