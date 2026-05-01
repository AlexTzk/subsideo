# Phase 09 Research: CSLC EGMS Third Number & Binding Reruns

**Phase:** 09 - CSLC EGMS Third Number & Binding Reruns
**Researched:** 2026-04-30
**Status:** Ready for planning

## Research Question

What needs to be known to plan Phase 9 well?

Phase 9 must convert the CSLC N.Am./EU validation cells from plain CALIBRATING outputs into audit-ready BINDING candidate outcomes: PASS, FAIL, or named BLOCKER. It must also close two deferred evidence paths: EU EGMS L2a stable-PS residual and Mojave amplitude-sanity disposition.

## Phase Inputs

### Requirements

- **CSLC-07:** `make eval-cslc-nam` and `make eval-cslc-eu` run with BINDING self-consistency gates calibrated from SoCal, Mojave/Coso-Searles, Iberian, and v1.2 added AOIs; the matrix no longer reports CSLC as merely CALIBRATING.
- **CSLC-10:** EU CSLC cell populates EGMS L2a stable-PS residual through the current EGMStoolkit class API or maintained adapter, without breaking numpy<2 validation environment.
- **CSLC-11:** Mojave/Coso-Searles has OPERA amplitude sanity or documented no reliable OPERA frame match evidence.
- **VAL-01:** CSLC cells rerun independently from cached intermediates and write validated `metrics.json` plus `meta.json` sidecars.
- **VAL-03:** `results/matrix.md` shows CSLC N.Am./EU outcomes with no empty cells and no collapsed product-quality/reference-agreement verdicts.

### Locked Context Decisions

- Use Phase 8 candidate thresholds: `median_of_persistent >= 0.75` and stable-terrain residual `<= 2.0 mm/yr`.
- Keep `criteria.py` CALIBRATING registry stable during reruns; write explicit candidate BINDING verdicts first, then promote registry only if rerun evidence supports it.
- EGMS blocker is acceptable only for current upstream access/API/tooling failure or scientifically insufficient stable PS support after filtering/clipping.
- EGMS blocker evidence must include request bounds, tool/package version, error/retry evidence, stable-PS counts before/after filtering/clipping, valid paired sample counts, `stable_std_max`, and `min_valid_points`.
- Mojave amplitude sanity should start with Mojave/Coso-Searles and record OPERA frame-search evidence for each attempted fallback.
- Matrix cells should leave plain CALIBRATING and report BINDING PASS, BINDING FAIL, or BINDING BLOCKER.
- Product-quality, reference-agreement, and blocker evidence must stay structurally distinct in sidecars and matrix rendering.
- Cached SAFEs/intermediates may be reused, but verdict-bearing metrics, sidecars, matrix output, and conclusions must be regenerated.

## Current Implementation Map

### N.Am. CSLC Eval

File: `run_eval_cslc_selfconsist_nam.py`

- `AOIConfig` has `run_amplitude_sanity`, but SoCal is `True` and Mojave fallback leaves are currently `False`.
- Mojave fallback chain is already concrete: Coso-Searles, Pahranagat, Amargosa.
- `_resolve_cell_status` supports `PASS`, `FAIL`, `CALIBRATING`, `MIXED`, `BLOCKER`, but leaf AOIs still return `status="CALIBRATING"`.
- The eval writes `eval-cslc-selfconsist-nam/metrics.json` as `CSLCSelfConsistNAMCellMetrics` plus `meta.json`.
- Existing amplitude sanity fetch uses `select_opera_frame_by_utc_hour` and `compare_cslc`, but it is gated off for Mojave leaves. Phase 9 must either turn it on for the selected Mojave fallback or write structured unavailable evidence when OPERA frame search cannot supply a reference.

### EU CSLC Eval

File: `run_eval_cslc_selfconsist_eu.py`

- `_fetch_egms_l2a` currently lazy-imports `EGMStoolkit` and calls `EGMStoolkit.download(...)` with bbox, `product_level="L2a"`, `release="2019_2023"`, and `output_dir`.
- The EGMS residual block catches every exception, logs it, sets `egms_residual = None`, and only includes `egms_l2a_stable_ps_residual_mm_yr` when residual is finite.
- That behavior is not enough for Phase 9. Plans must convert missing EGMS into a named blocker with structured evidence rather than a silent null.
- EU amplitude sanity is best effort. OPERA CSLC-S1 V1 availability may be N.Am.-only, so the planner should avoid making EU OPERA amplitude sanity a hard gate unless current reference access proves available.

### EGMS Residual Helper

File: `src/subsideo/validation/compare_cslc.py`

- `compare_cslc_egms_l2a_residual` filters EGMS PS points with `mean_velocity_std < stable_std_max` where default `stable_std_max=2.0`.
- It clips stable PS points to raster bounds, samples the CSLC velocity raster, applies nodata filtering, enforces `min_valid_points=100`, reference-aligns by subtracting the median of sampled CSLC velocities, and returns mean absolute residual.
- It currently returns only a float or NaN. It logs counts, but the counts are not returned to callers. Phase 9 needs either a diagnostic-return extension or a wrapper that captures enough evidence for blocker sidecars.

### Sidecar Schema

File: `src/subsideo/validation/matrix_schema.py`

- `AOIResult.status` supports `PASS`, `FAIL`, `CALIBRATING`, `BLOCKER`, `SKIPPED`.
- `CSLCSelfConsistNAMCellMetrics.cell_status` supports `PASS`, `FAIL`, `CALIBRATING`, `MIXED`, `BLOCKER`.
- `CSLCSelfConsistEUCellMetrics` inherits from N.Am. and currently records EGMS residual only as an optional measurement nested in `per_aoi[].product_quality.measurements`.
- Schema has no first-class candidate BINDING verdict fields and no first-class blocker-evidence structure. Phase 9 likely needs additive fields, preserving Pydantic `extra="forbid"` discipline.

### Criteria Registry

File: `src/subsideo/validation/criteria.py`

- Current CSLC self-consistency criteria are CALIBRATING:
  - `cslc.selfconsistency.coherence_min`: `> 0.7`
  - `cslc.selfconsistency.residual_mm_yr_max`: `< 5.0`
  - both have `binding_after_milestone="v1.2"`.
- Phase 9 candidate thresholds are stricter:
  - `median_of_persistent >= 0.75`
  - `residual_mm_yr <= 2.0`
- Do not silently edit the registry at the start of the phase. Plans should first add candidate-verdict computation and tests, then make any registry promotion a final guarded task only after rerun evidence supports it.

### Matrix Writer

File: `src/subsideo/validation/matrix_writer.py`

- `_render_cslc_selfconsist_cell` detects `per_aoi` sidecars, validates N.Am./EU metrics classes, and always appends `status_label += " -- binds v1.2"`.
- It italicises the product-quality column as CALIBRATING discipline and renders EGMS residual only when present.
- It does not render `BINDING PASS`, `BINDING FAIL`, or `BINDING BLOCKER`.
- Phase 9 should add rendering for explicit candidate BINDING fields without collapsing product-quality, reference-agreement, and blocker evidence.

### Tests

Existing relevant tests:

- `tests/unit/test_matrix_schema.py` covers `AOIResult`, `CSLCSelfConsistNAMCellMetrics`, and `CSLCSelfConsistEUCellMetrics`.
- `tests/unit/test_matrix_writer.py` covers CSLC self-consistency shape detection, CALIBRATING rendering, MIXED/BLOCKER rendering, EU EGMS third-number rendering, and Makefile target wiring.
- `tests/unit/test_criteria_registry.py` pins current CSLC self-consistency thresholds/type/binding metadata.
- `tests/unit/test_run_eval_cslc_selfconsist_nam.py` and `tests/unit/test_run_eval_cslc_selfconsist_eu.py` contain script-source and behavior tests for the eval scripts.

### Make Targets

File: `Makefile`

- `make eval-cslc-nam` runs `micromamba run -n subsideo python -m subsideo.validation.supervisor run_eval_cslc_selfconsist_nam.py`.
- `make eval-cslc-eu` runs the EU self-consistency script.
- `make results-matrix` runs `python -m subsideo.validation.matrix_writer --out results/matrix.md`.

## Phase 8 Evidence to Preserve

Canonical artifact: `.planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md`

Useful rows:

- SoCal: `t144_308029_iw1`, OPERA CSLC coverage count 2089.
- Mojave/Coso-Searles: `t064_135527_iw2`, OPERA CSLC coverage count 864.
- Mojave/Pahranagat: `t173_370296_iw2`, OPERA CSLC coverage count 451.
- Mojave/Amargosa: `t064_135530_iw3`, OPERA CSLC coverage count 899.
- Iberian Meseta-North: `t103_219329_iw1`, EGMS L2a stable-PS ceiling 250876, OPERA CSLC count 0.
- Ebro Basin and La Mancha are accepted EU fallback AOIs, but burst IDs still need derivation from the EU burst DB before eval wiring.

Planner implication: Mojave amplitude sanity should be attempted on the real runnable fallback chain, starting with Coso-Searles. EU fallback wiring should not become a surprise Phase 9 expansion unless needed to resolve an EGMS stable-PS blocker and the burst derivation is low-risk.

## Likely Implementation Slices

### Slice 1: Candidate BINDING Sidecar Contract

Add additive schema fields for candidate BINDING verdicts and blocker evidence:

- Candidate thresholds used: coherence threshold `0.75`, residual threshold `2.0`.
- Candidate cell verdict: `BINDING PASS`, `BINDING FAIL`, or `BINDING BLOCKER`.
- Per-AOI candidate verdicts, preserving current `status` compatibility.
- Blocker evidence with reason category and audit evidence.

Keep old CALIBRATING criteria intact in `criteria.py` until closure.

### Slice 2: EGMS L2a Residual Diagnostics

Extend EGMS residual handling so missing `egms_l2a_stable_ps_residual_mm_yr` becomes an explicit blocker unless the residual is populated.

Potential approach:

- Add a diagnostic object around `compare_cslc_egms_l2a_residual` that records:
  - bbox/request bounds
  - EGMStoolkit version if import succeeds
  - CSV paths/counts
  - total PS, stable PS after `mean_velocity_std < stable_std_max`, in-raster PS, valid paired PS
  - `stable_std_max=2.0`
  - `min_valid_points=100`
  - exception class/message and retry count if fetch fails
- Preserve the current float-return helper if many callers depend on it; add a new helper or optional diagnostics return rather than breaking callers.

### Slice 3: Mojave OPERA Amplitude Sanity

Enable amplitude sanity for selected Mojave fallback leaves or add a separate frame-search evidence path.

Potential approach:

- Add `run_amplitude_sanity=True` to Mojave fallback leaf configs only if OPERA frame search is expected to succeed.
- If no HDF5 reference is found, store OPERA search evidence instead of only logging a warning.
- Keep fallback order bounded to Coso-Searles, then Pahranagat/Amargosa only if needed. Do not broaden into a new AOI search project.

### Slice 4: Matrix Rendering and Tests

Teach `_render_cslc_selfconsist_cell` to prefer explicit candidate BINDING verdict fields when present:

- PASS/FAIL/BLOCKER wording should be non-CALIBRATING and visibly include BINDING.
- Product-quality column should render coherence/residual/EGMS residual or blocker details.
- Reference-agreement column should render amplitude sanity or unavailable disposition separately.
- Legacy CALIBRATING sidecars should continue rendering via the old path for backward compatibility.

### Slice 5: Rerun and Closure

Run the expensive evals and matrix regeneration:

- `make eval-cslc-eu`
- `make eval-cslc-nam`
- `make results-matrix`

If candidate evidence passes, perform guarded registry promotion:

- Update `criteria.py` threshold/type entries only after regenerated sidecars exist.
- Update tests that currently pin CALIBRATING thresholds.
- Record promotion in conclusions/methodology only if evidence supports it; otherwise leave a named blocker or narrowed promotion disposition.

## Risks and Pitfalls

- **Silent EGMS null:** Current EU script swallows all EGMS exceptions and omits the residual measurement. This directly violates Phase 9 unless replaced by populated residual or named blocker evidence.
- **Wrong status vocabulary:** Current sidecar `status` literals do not include strings with spaces like `BINDING PASS`. Use separate candidate verdict fields or extend literals carefully.
- **Registry before evidence:** Editing `criteria.py` early would reinterpret old sidecars and break the dual-record transition decision.
- **Pydantic extra-forbid:** Any sidecar extension must be represented in `matrix_schema.py`; ad hoc JSON keys will fail validation.
- **Mojave scope creep:** Do not search arbitrary nearby frames. Use Phase 8 fallback chain and record unavailable evidence when frame search fails.
- **Network/API instability:** `make eval-cslc-eu` and `make eval-cslc-nam` depend on credentials, ASF/Earthdata, EGMS tooling, and OPERA references. Plans need explicit blocker acceptance criteria for upstream failures.
- **Long runtime:** Cold CSLC evals are many hours. Plans should emphasize warm reruns from cached verified inputs and targeted unit tests before expensive commands.

## Validation Architecture

### Unit-Level Validation

Recommended focused tests:

- `pytest tests/unit/test_matrix_schema.py`
- `pytest tests/unit/test_matrix_writer.py`
- `pytest tests/unit/test_criteria_registry.py`
- `pytest tests/unit/test_run_eval_cslc_selfconsist_eu.py`
- `pytest tests/unit/test_run_eval_cslc_selfconsist_nam.py`

Add or update tests for:

- Candidate BINDING sidecar schema accepts PASS/FAIL/BLOCKER without breaking legacy CALIBRATING sidecars.
- EU EGMS residual diagnostics distinguish populated residual, insufficient stable PS, upstream/tooling failure, and adapter/schema mismatch.
- Mojave amplitude sanity evidence records OPERA frame search outcome for Coso-Searles and any attempted fallback.
- Matrix renders `BINDING PASS`, `BINDING FAIL`, and `BINDING BLOCKER` without italic CALIBRATING text when candidate verdict fields are present.
- Legacy Phase 3 sidecars still render as CALIBRATING.

### Integration-Level Validation

Primary phase commands:

- `make eval-cslc-eu`
- `make eval-cslc-nam`
- `make results-matrix`

Expected artifacts:

- `eval-cslc-selfconsist-eu/metrics.json`
- `eval-cslc-selfconsist-eu/meta.json`
- `eval-cslc-selfconsist-nam/metrics.json`
- `eval-cslc-selfconsist-nam/meta.json`
- `results/matrix.md`
- Updated CSLC conclusions files if evidence changes the scientific disposition.

Acceptance checks:

- EU metrics include finite `egms_l2a_stable_ps_residual_mm_yr` or a named blocker with EGMS evidence fields.
- N.Am. metrics include Mojave/Coso-Searles amplitude sanity or unavailable disposition with OPERA frame-search evidence.
- `results/matrix.md` CSLC N.Am./EU rows do not read only as CALIBRATING.
- Sidecars parse through Pydantic schemas.
- Cached-input reuse is visible through `meta.json` input hashes/provenance.

## Planning Recommendations

Recommended plan split:

1. Schema and candidate-verdict contract, with unit tests.
2. EGMS L2a diagnostics/blocker handling, with focused tests.
3. Mojave amplitude-sanity evidence path, with focused tests.
4. Matrix rendering and conclusions wording for BINDING PASS/FAIL/BLOCKER.
5. Expensive rerun and guarded criteria promotion or explicit blocker closure.

The planner should keep rerun execution in the final wave after schema/rendering logic is tested. It should also mark any command requiring live credentials/network as potentially non-autonomous or blocker-aware.

## Research Complete

This research supports planning Phase 09 with concrete code entry points, risks, validation commands, and plan slice boundaries.
