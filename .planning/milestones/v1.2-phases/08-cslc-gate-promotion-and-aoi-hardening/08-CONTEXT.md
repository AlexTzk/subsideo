# Phase 8: CSLC Gate Promotion & AOI Hardening - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 8 hardens the CSLC validation inputs before gate promotion. It fixes projected-metre stable-terrain buffering, regenerates acquisition-backed AOI probe artifacts, validates fallback AOIs, rejects truncated SAFE caches before readers consume them, fixes v1.1 shared-infra defects, retires stale tests, and proposes CSLC BINDING thresholds grounded in v1.1 plus any Phase 8 diagnostics. Phase 9 owns the binding reruns and final promotion.

</domain>

<decisions>
## Implementation Decisions

### Stable-Terrain Buffer Fix
- **D-01:** Preserve the current stable-mask defaults: `coast_buffer_m=5000.0`, `water_buffer_m=500.0`, and `slope_max_deg=10.0`. Phase 8 should fix projection/CRS handling so coast and water buffers are demonstrably applied in metres, not lon/lat degrees.
- **D-02:** Add diagnostics with the fix. At minimum, report stable-mask retention metrics for SoCal, Mojave/Coso-Searles, and Iberian Meseta-North so the SoCal coastal sparse-mask story is explainable and threshold proposal evidence is auditable.
- **D-03:** Visual artifacts such as stable-mask-over-basemap and coherence histograms are optional planner discretion unless needed to explain a surprising retention change. Do not make Phase 8 primarily a visual artifact phase.

### AOI Probe Regeneration
- **D-04:** Fully regenerate the CSLC AOI probe artifact from real ASF/CDSE acquisition searches. This includes SoCal, all Mojave fallbacks, Iberian Meseta-North, and at least two EU fallback AOIs.
- **D-05:** Treat the regenerated artifact as the new source of truth for Phase 9 reruns. Do not patch around the v1.1 fabricated/invalid rows; replace them with search-backed sensing windows, rejected-candidate reasoning, and selected date tuples.
- **D-06:** The probe should record enough evidence for downstream trust: search parameters, selected SAFE/acquisition identifiers, rejected candidates and reasons, and which fallbacks are validated for future use.

### SAFE Cache Self-Healing
- **D-07:** Implement SAFE cache self-healing at both layers: downloader-level validation prevents newly truncated archives from being exposed, and a shared harness/eval setup guard scans existing cached SAFEs before reuse.
- **D-08:** The shared guard belongs in validation infrastructure, not in only one eval script. CSLC, DISP, and RTC eval setup paths should benefit before `s1reader`, `compass`, or `opera-rtc` attempts to read a poisoned cache.
- **D-09:** The behavior should redownload or force redownload on detected truncation/incomplete zip state; failures must surface clearly rather than letting a reader fail later with a low-level archive or HDF5 error.

### Binding Threshold Rationale
- **D-10:** Phase 8 should propose a conservative CSLC BINDING gate: coherence `>= 0.75` using the locked `median_of_persistent` gate metric, and stable-terrain residual `<= 2.0 mm/yr`.
- **D-11:** The rationale must explicitly reference the v1.1 calibration values: SoCal coherence `0.887` / residual `-0.109 mm/yr`, Mojave/Coso-Searles coherence `0.804` / residual `+1.127 mm/yr`, and Iberian coherence `0.868` / residual `+0.347 mm/yr`.
- **D-12:** Phase 8 proposes the rationale; Phase 9 performs reruns and final promotion. If Phase 8 diagnostics or new fallback AOI values materially undercut the conservative proposal, document that as evidence rather than silently moving the gate.

### Stale Tests and Shared-Infra Defects
- **D-13:** Fix the real shared-infra defects CR-01, CR-02, and HI-01 with regression tests. These are in scope because they block or de-risk CSLC/DISP reruns that consume shared validation infrastructure.
- **D-14:** For `test_env07_diff_discipline` and `test_iberian_aoi_fallback_chain_two_entries`, preserve useful behavioral coverage but do not force awkward v1.1 script structure just to satisfy stale assertions.
- **D-15:** Update or relax stale tests if they still guard real behavior after probe regeneration. Remove them with documented rationale if better invariants cover the regenerated AOI artifact, fallback semantics, and script parity where it matters.

### the agent's Discretion
- Exact layout of retention diagnostics in metrics sidecars vs conclusions docs.
- Whether visual sanity artifacts are required after the buffer fix.
- Exact implementation split between downloader helpers and harness cache scanner.
- Exact test names and schema shape for cache-integrity and regenerated-probe regressions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` - Phase 8 goal, dependencies, requirements, and six success criteria.
- `.planning/REQUIREMENTS.md` - CSLC-07, CSLC-08, CSLC-09, CSLC-12, RTCSUP-01, and RTCSUP-03 requirement text.
- `.planning/PROJECT.md` - v1.2 milestone focus, metrics-vs-targets discipline, CSLC/DISP product-quality and reference-agreement separation, and out-of-scope boundaries.
- `.planning/STATE.md` - v1.2 current position and accumulated v1.1 decisions.

### Prior CSLC decisions and evidence
- `.planning/milestones/v1.1-phases/03-cslc-s1-self-consistency-eu-validation/03-CONTEXT.md` - gate metric lock (`median_of_persistent`), CALIBRATING discipline, AOI probe pattern, stable-mask source decisions, and methodology policy.
- `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` - SoCal and Mojave/Coso-Searles v1.1 metrics, fabricated N.Am. tuple follow-up, SoCal coast-buffer follow-up, and Mojave amplitude-sanity follow-up.
- `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` - Iberian Meseta-North v1.1 metrics, invalid EU fallback rows, stale-test notes, and EGMS third-number deferral.
- `docs/validation_methodology.md` - product-quality vs reference-agreement discipline and CALIBRATING-to-BINDING methodology context.

### Shared infrastructure and audit findings
- `.planning/milestones/v1.1-phases/04-disp-s1-comparison-adapter-honest-fail/04-CONTEXT.md` - DISP/CSLC shared validation infrastructure context and HI-01/CR-style regression discipline.
- `.planning/milestones/v1.1-phases/07-results-matrix-release-readiness/07-CONTEXT.md` - CSLC data-point count, binding annotation policy, and matrix closure context.
- `.planning/milestones/v1.1-phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-REVIEW.md` - CR-01 and CR-02 review findings and recommended fixes.

### Code entry points
- `src/subsideo/validation/stable_terrain.py` - `build_stable_mask` and buffered geometry rasterization.
- `tests/unit/test_stable_terrain.py` - current stable-terrain unit coverage; needs projected-metre and multi-UTM strengthening.
- `scripts/probe_cslc_aoi_candidates.py` - existing CSLC AOI probe script to regenerate and harden.
- `run_eval_cslc_selfconsist_nam.py` - SoCal plus Mojave fallback-chain eval script.
- `run_eval_cslc_selfconsist_eu.py` - Iberian eval script and stale-test target.
- `src/subsideo/validation/harness.py` - shared validation plumbing, retry policy, existing `find_cached_safe`, and expected home for cache scanning.
- `src/subsideo/validation/compare_disp.py` - CR-01 and HI-01 affected area; already contains evidence of the intended fix pattern in current code.
- `tests/unit/test_run_eval_cslc_selfconsist_eu.py` - stale tests called out by Phase 8.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `stable_terrain.build_stable_mask`: already accepts coastline/waterbody geometries, `transform`, `crs`, and metre buffer distances. Phase 8 should harden CRS/projection behavior and tests rather than invent a new mask builder.
- `scripts/probe_cslc_aoi_candidates.py`: existing probe structure covers Mojave/Iberian candidates, artifact generation, and review prompts; Phase 8 should replace fabricated/invalid rows through a real search-backed regeneration.
- `harness.download_reference_with_retry`: already streams through a `.partial` file and atomically renames on success. Phase 8 should extend archive completeness validation around this discipline rather than bypass it.
- `harness.find_cached_safe`: existing cross-cell SAFE reuse helper. Phase 8 can pair this with a truncation/integrity checker before returning or consuming cached SAFE paths.
- `matrix_schema.AOIResult` and CSLC self-consistency metrics: existing nested AOI and fallback-chain model can carry regenerated AOI/fallback status without reshaping the matrix from scratch.

### Established Patterns
- Probe artifacts are committed as planning/research evidence before expensive eval runs.
- Eval scripts use declarative AOI lists and per-AOI/fallback isolation so one failed candidate does not hide other results.
- Validation metrics are sidecar-first (`metrics.json` / `meta.json`) and matrix output is rendered from sidecars, not parsed from conclusions prose.
- CALIBRATING gates become BINDING only after enough evidence; Phase 8 proposes thresholds, Phase 9 applies them through reruns.
- Shared validation infrastructure fixes require regression tests, especially when they prevent silent bad data or misleading retry behavior.

### Integration Points
- Stable-mask fix connects `src/subsideo/validation/stable_terrain.py`, `tests/unit/test_stable_terrain.py`, and CSLC eval scripts that pass WorldCover, slope, coastline, and waterbody inputs.
- Probe regeneration connects `scripts/probe_cslc_aoi_candidates.py`, `.planning/milestones/v1.2-research/` or the Phase 8 artifact directory, and both CSLC eval scripts.
- Cache self-healing connects downloader helpers, `harness.find_cached_safe`, CSLC/DISP/RTC eval setup, and cache directories such as `eval-cslc-selfconsist-*` and `eval-disp-*`.
- Shared-infra fixes connect `harness.py`, `compare_disp.py`, and tests covering HTTP retry semantics, raster nodata lifecycle, and `reproject(..., dst_nodata=np.nan)`.

</code_context>

<specifics>
## Specific Ideas

- The threshold proposal should be written as a rationale, not a final Phase 9 verdict: `coherence >= 0.75` and `residual <= 2.0 mm/yr` are the Phase 8 recommendation if diagnostics remain consistent with v1.1.
- SoCal retention metrics are essential because v1.1 accepted a sparse coastal stable mask while explicitly tracking the unit/projection bug for later fix.
- The regenerated AOI probe should remove the old "fabricated dates" ambiguity entirely. Future agents should not have to know which v1.1 rows were real, invalid, or patched post hoc.
- Cache healing should protect both newly downloaded files and stale local caches. The latter matters because v1.1/v1.2 work reuses large S1 downloads across cells.
- Stale tests should be judged by behavioral value. Script parity and fallback semantics are important; exact v1.1 structure is not.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 8 scope.

</deferred>

---

*Phase: 08-cslc-gate-promotion-and-aoi-hardening*
*Context gathered: 2026-04-30*
