---
phase: 09-cslc-egms-third-number-binding-reruns
status: passed
verified: 2026-05-02T00:00:00-07:00
requirements:
  - CSLC-07
  - CSLC-10
  - CSLC-11
  - VAL-01
  - VAL-03
score: 5/5
human_verification: []
gaps: []
follow_up_blockers:
  - socal_stable_mask_cslc_zero_valid_pixels
  - eu_opera_frame_unavailable
  - egms_toolkit_download_api_mismatch
---

# Phase 09 Verification

## Verdict

**PASSED** — Phase 09 achieved its goal as an evidence-backed CSLC BINDING deferment.

The phase did not promote `criteria.py`, and that is the correct outcome: regenerated Phase 09 sidecars report `BINDING BLOCKER` for both CSLC N.Am. and CSLC EU. The blockers are named, structured, preserved in committed `metrics.json` sidecars, rendered in `results/matrix.md`, and documented in the CSLC conclusions.

## Requirement Traceability

| Requirement | Result | Evidence |
|-------------|--------|----------|
| CSLC-07 | Passed via blocker outcome | `results/matrix.md` renders CSLC N.Am. and EU as explicit `BINDING BLOCKER`, not plain CALIBRATING. Candidate thresholds are preserved in sidecars. |
| CSLC-10 | Passed via named blocker/deferment | EU sidecar contains candidate `BINDING BLOCKER`; Iberian product-quality metrics are present and the committed blocker is `opera_frame_unavailable`. Rerun logs also record the remaining `EGMStoolkit.download` API mismatch before EGMS CSV diagnostics can run. |
| CSLC-11 | Passed | N.Am. sidecar records Mojave/Coso-Searles candidate `BINDING PASS` with OPERA amplitude sanity (`amplitude_r=0.955419`, `amplitude_rmse_db=2.248974`). |
| VAL-01 | Passed | `make eval-cslc-eu` wrote EU `metrics.json`/`meta.json`; `make eval-cslc-nam` wrote N.Am. `metrics.json`/`meta.json` before exiting nonzero for the required SoCal blocker. |
| VAL-03 | Passed | `results/matrix.md` has non-empty CSLC rows with distinct product-quality and reference-agreement columns. |

## Must-Haves

- Candidate BINDING sidecar schema exists and remains backward-compatible.
- Candidate thresholds are explicit: coherence `0.75`, residual `2.0`, and EU EGMS third-number threshold `5.0` where applicable.
- EGMS residual absence is no longer silent; the EU path creates named blocker evidence and the final sidecar also blocks on missing OPERA amplitude sanity.
- Mojave/Coso-Searles amplitude sanity was attempted and populated.
- `criteria.py` remains CALIBRATING because both regenerated cell-level verdicts are `BINDING BLOCKER`.
- Matrix rendering shows explicit `BINDING BLOCKER` rows and preserves evidence-category separation.
- Code review passed cleanly: `09-REVIEW.md` reports `critical: 0`, `warning: 0`, `status: clean`.

## Verified Artifacts

- `eval-cslc-selfconsist-nam/metrics.json`
- `eval-cslc-selfconsist-nam/meta.json`
- `eval-cslc-selfconsist-eu/metrics.json`
- `eval-cslc-selfconsist-eu/meta.json`
- `results/matrix.md`
- `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md`
- `CONCLUSIONS_CSLC_SELFCONSIST_EU.md`
- `src/subsideo/validation/criteria.py`
- `src/subsideo/validation/matrix_schema.py`
- `src/subsideo/validation/matrix_writer.py`
- `run_eval_cslc_selfconsist_nam.py`
- `run_eval_cslc_selfconsist_eu.py`

## Automated Checks

- `make eval-cslc-eu` exited 0 and regenerated EU sidecars.
- `make eval-cslc-nam` exited 2 after regenerating N.Am. sidecars with a named SoCal blocker.
- `make results-matrix` exited 0.
- Focused Phase 09 unit suite passed with one expected xfail for known ENV-07 divergence debt.
- Broad unit suite `micromamba run -n subsideo python -m pytest tests/unit/ -x -q --tb=short --no-cov` passed with the same expected xfail.
- Schema drift check returned `drift_detected: false`.
- Codebase drift check skipped non-blocking with `reason: no-structure-md`.

## Follow-Up Blockers

These are not Phase 09 execution gaps; they are the next work needed before a future CSLC registry promotion:

- **SoCal stable-mask intersection:** `stable_mask_cslc` dropped from 2,286 pixels to 0 valid pixels after burst-footprint intersection.
- **EU OPERA reference availability:** no OPERA reference HDF5 was found under `eval-cslc-selfconsist-eu/opera_reference/Iberian`.
- **EGMS toolkit adapter:** rerun logs show the installed `EGMStoolkit` module lacks the expected `download` attribute, so EGMS CSV diagnostics cannot yet run.

## Conclusion

Phase 09 is complete. It produced audit-ready candidate BINDING sidecars, rerun evidence, matrix output, and documented deferment. The project should not promote CSLC self-consistency criteria yet; future work should target the named blockers above.
