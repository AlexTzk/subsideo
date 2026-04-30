# Requirements: v1.2 CSLC Binding & DISP Science Pass

## Milestone Goal

Promote CSLC-S1 from CALIBRATING to BINDING product-quality validation and turn DISP-S1's v1.1 honest FAIL into an actionable science pass or a narrowed, evidence-backed blocker, focusing on N.Am. and EU cells. RTC-S1 work is included only where it directly supports shared validation infrastructure, cached input integrity, orbit/DEM diagnostics, or CSLC/DISP reruns.

## Requirements

### CSLC-S1

- [ ] **CSLC-07**: User can run `make eval-cslc-nam` and `make eval-cslc-eu` with BINDING self-consistency gates whose thresholds are calibrated from the v1.1 SoCal, Mojave/Coso-Searles, and Iberian results plus any v1.2 added AOIs; the matrix no longer reports CSLC as merely CALIBRATING.
- [ ] **CSLC-08**: User can inspect stable-terrain masks whose coast and water buffers are projected in metres before buffering, with regression tests proving the mask is geometrically correct across UTM zones and does not silently over-trim SoCal-style coastal bursts.
- [ ] **CSLC-09**: User can regenerate CSLC AOI probe artifacts from real ASF/CDSE acquisition searches, with fabricated sensing windows removed and validated burst/date tuples for the existing N.Am. AOIs plus at least two EU fallback AOIs beyond Iberian Meseta-North.
- [ ] **CSLC-10**: User can run the EU CSLC cell with the EGMS L2a stable-PS residual populated through the current EGMStoolkit class API or a maintained adapter, without breaking the numpy<2 validation environment.
- [ ] **CSLC-11**: User can run OPERA amplitude sanity for the successful Mojave/Coso-Searles fallback, or read a documented reason why no reliable OPERA frame match exists for that burst.
- [ ] **CSLC-12**: User runs `pytest tests/unit/test_env07_diff_discipline.py` and `pytest tests/unit/test_iberian_aoi_fallback_chain_two_entries.py` and either both pass on the post-AOI-regeneration codebase or are explicitly removed with rationale, so v1.1 stale-test debt does not carry forward.

### DISP-S1

- [ ] **DISP-06**: User can rerun SoCal and Bologna DISP evaluations from cached CSLC stacks with an ERA5 tropospheric-correction toggle, and the conclusions report whether ramp magnitude, ramp direction stability, r, bias, and RMSE improve relative to the v1.1 baseline.
- [ ] **DISP-07**: User can apply a PHASS post-deramping candidate to the v1.1 cached DISP stacks without changing the native 5 x 10 m production output, and compare product-quality and reference-agreement metrics against the unchanged v1.1 reference pipeline.
- [ ] **DISP-08**: User can run at least one alternative unwrapper/resolution candidate from the v1.1 brief, selected from SPURT native, tophu/SNAPHU tiled, or 20 x 20 m fallback, with failure modes captured as structured metrics rather than terminal-only logs.
- [ ] **DISP-09**: User can compare DISP candidate outputs on both N.Am. OPERA and EU EGMS references using the existing `prepare_for_reference(method=...)` discipline, with product-quality, reference-agreement, and ramp-attribution reported separately.
- [ ] **DISP-10**: User can open updated DISP conclusions that choose a next production posture: PASS, keep PHASS with deramping, switch unwrapper, use a coarser validation fallback, or defer with one remaining named blocker and dated unblock condition.

### RTC-S1 Support Only

- [ ] **RTCSUP-01**: User can rely on shared validation cache handling to reject truncated SAFE zip files before CSLC/DISP/RTC readers consume them, preventing interrupted downloads from poisoning reruns.
- [ ] **RTCSUP-02**: User can run shared orbit and DEM provenance diagnostics that explain whether RTC EU Alpine/Iberian drift is due to version, orbit, DEM/slope, or terrain effects when those diagnostics are needed to interpret CSLC/DISP failures.
- [ ] **RTCSUP-03**: User can rerun DISP/CSLC validations without hitting the v1.1 audit-flagged shared-infra defects: CR-01 (`compare_disp.py:319` `src.nodata` accessed after rasterio context closes — raises on EGMS L2a comparison), CR-02 (`harness.py:515` `raise_for_status()` HTTPError silently swallowed by retry), and HI-01 (`compare_disp.py:543-586` `reproject()` lacks `dst_nodata=np.nan`).

### Matrix, Methodology, and Release Readiness

- [ ] **VAL-01**: User can run `make eval-cslc-nam`, `make eval-cslc-eu`, `make eval-disp-nam`, and `make eval-disp-eu` independently from cached intermediates, and each cell writes validated `metrics.json` plus `meta.json` sidecars consumed by the manifest-driven matrix.
- [ ] **VAL-02**: User can read `docs/validation_methodology.md` and find v1.2 additions covering CSLC gate promotion, EGMS L2a residual handling, DISP ERA5/deramping/unwrapper diagnostics, and the conditions under which CALIBRATING gates became BINDING.
- [ ] **VAL-03**: User can open `results/matrix.md` and see v1.2 CSLC/DISP N.Am./EU outcomes with no empty cells and no collapsed product-quality/reference-agreement verdicts.
- [ ] **VAL-04**: User opens the consolidated REQUIREMENTS.md traceability table after v1.2 closure and finds zero stale "Pending" rows for v1.1 requirements that VERIFICATION.md marked SATISFIED, plus every v1.2 requirement mapped to exactly one phase.

## Future Requirements

- DIST-S1 operational OPERA reference comparison when `OPERA_L3_DIST-ALERT-S1_V1` publishes.
- DSWx-S2 EU recalibration / fit-set quality review after the CSLC/DISP milestone closes.
- RTC-S1 EU Fire-burst substitution or upstream opera-rtc Topo bug filing, unless a CSLC/DISP dependency makes it urgent.
- RTC-S1 VH parity across EU bursts, unless needed for shared comparison infrastructure.

## Out of Scope

- New product classes or global expansion beyond the existing N.Am./EU validation matrix.
- Moving native CSLC/DISP product resolution away from OPERA-spec 5 x 10 m as a production default.
- ML-based replacements for DISP unwrapping or DSWx thresholds.
- DIST-S1 and DSWx-S2 remediation work, except for incidental harness fixes shared with CSLC/DISP.

## Traceability

| Requirement | Phase |
|-------------|-------|
| CSLC-07 | Phase 8 |
| CSLC-08 | Phase 8 |
| CSLC-09 | Phase 8 |
| CSLC-10 | Phase 9 |
| CSLC-11 | Phase 9 |
| CSLC-12 | Phase 8 |
| DISP-06 | Phase 10 |
| DISP-07 | Phase 11 |
| DISP-08 | Phase 11 |
| DISP-09 | Phase 11 |
| DISP-10 | Phase 12 |
| RTCSUP-01 | Phase 8 |
| RTCSUP-02 | Phase 10 |
| RTCSUP-03 | Phase 8 |
| VAL-01 | Phase 12 |
| VAL-02 | Phase 12 |
| VAL-03 | Phase 12 |
| VAL-04 | Phase 12 |
