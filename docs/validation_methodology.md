# Validation Methodology

**Scope:** Consolidates cross-cutting validation-methodology findings that span
multiple phases and products. Updated append-only per phase — Phase 3 writes
section 1 + section 2; Phase 4 will append the DISP ramp-attribution section;
Phases 5/6 will append the DSWE F1 ceiling and cross-sensor precision-first
sections; Phase 7 REL-03 will write the top-level table of contents and the
final cross-section consistency pass.

> This document is for us-future-selves and external contributors. The policy
> statements here close specific "wasted re-attempt" anti-patterns the team has
> already hit once (see `.planning/research/PITFALLS.md` §P2.4 and §M1–M6 for
> the underlying source material).

---

## 1. CSLC cross-version phase impossibility

<a name="cross-version-phase"></a>

**TL;DR:** Interferometric phase comparison between CSLCs produced by different
isce3 **major** versions yields coherence ≈ 0 regardless of which phase
corrections are applied on top. Amplitude-based metrics (correlation, RMSE in
dB) remain valid across versions. **Do NOT re-attempt with additional
corrections.**

### 1.1 Structural argument — the SLC interpolation kernel changed

Between isce3 0.15 and 0.25 (and almost certainly at or before isce3 0.19 — see
the upstream [isce3 Releases page](https://github.com/isce-framework/isce3/releases)
for the SLC-interpolation entries in the 0.15 → 0.19 range), the **SLC
interpolation kernel itself** changed. The kernel change is upstream of every
phase-screen correction normally enumerated when InSAR practitioners debug
coherence loss:

1. The CSLC geocoding step samples the native-grid Sentinel-1 SLC complex
   values onto the target geocoded grid. Sub-pixel sample weights are set by
   the interpolation kernel.
2. Changing the kernel (sinc → raised-cosine, kernel-width change, sub-kernel
   optimisation, anti-aliasing factor) changes the complex value at every
   geocoded pixel by a sub-pixel-scale phase amount that is a function of the
   kernel itself, not of any correction term that comes after.
3. **Two CSLCs computed from the same SLC with different interpolation kernels
   produce different absolute phase values at every pixel.** No amount of
   downstream phase correction (carrier removal, ellipsoidal flattening,
   tropospheric correction, solid Earth tide, ionospheric delay, range bistatic
   correction, azimuth FM-rate variation) can recover the original phase
   values, because none of those correction terms is the kernel.

The only "correction" that would recover cross-version phase equivalence is
**regenerating the OPERA CSLC with the newer isce3 kernel**, at which point it
is just re-running the pipeline and the comparison is no longer a cross-version
check. Equivalently: there is no post-processing operator that inverts the
kernel difference because the kernel difference is not an additive phase screen
in any tractable basis.

### 1.2 Policy statement

**Do NOT re-attempt with additional corrections.** A pull request titled
"CSLC phase comparison: additional corrections" touching
`src/subsideo/validation/compare_cslc.py` (or any future
`src/subsideo/validation/compare_disp.py` cross-chain branch) **MUST address
in its description why the SLC-interpolation-kernel argument from §1.1 no
longer holds** before merge. Adding another correction term — ionospheric,
solid Earth tide, fallback flattening, stratospheric delay, troposphere,
tropopause height, antenna pattern, range walk — does NOT constitute
addressing the argument; all of those corrections are downstream of the
kernel.

The only merge-able argument is empirical evidence of kernel stability across
the specific isce3 version pair at issue (e.g. 0.25.8 vs 0.25.10 within the
same minor series — see `.planning/research/PITFALLS.md` §P2.4 for the optional
diagnostic-experiment menu, currently flagged LOW confidence and not blocking
any milestone).

Reviewers: a rerun showing coherence improving from 0.0003 to 0.0015 is NOT
progress; both are random noise. A PR description shaped like "subtract X plus
Y plus Z and it might work this time" is a code smell.

### 1.3 Diagnostic Evidence (Appendix)

The following is *corroborating evidence*, not the lead argument. The v1.0
N.Am. CSLC-S1 validation session (`CONCLUSIONS_CSLC_N_AM.md` §5.3) ran the
exhaustive correction-removal experiment on burst `t144_308029_iw1` comparing
our chain (isce3 0.25.8) against the OPERA reference (isce3 0.15.1):

| Test | Coherence |
|------|-----------|
| Raw cross-version compare (no correction removed) | 0.0003 |
| Carrier phase removed from both | 0.002 |
| Flattening phase removed from both | 0.003 |
| Carrier + flattening removed from both | 0.002 |
| Reference's carrier + flattening applied to our product | 0.002 |

All values are random-noise coherence. The phase difference standard deviation
is 2.57 rad after carrier removal and 2.59 rad after flattening removal —
uniform-over-2π noise, uninformative. See `CONCLUSIONS_CSLC_N_AM.md` §5.3 for
the full diagnostic report and §5.4 for the original "implications for
methodology" framing this section consolidates.

**Implication:** amplitude-based cross-version validation (correlation + RMSE
on magnitude) is the correct reference-agreement path when isce3 majors
differ. `subsideo.validation.compare_cslc.compare_cslc` returns amplitude-based
`ReferenceAgreementResult`; the BINDING criteria `cslc.amplitude_r_min = 0.6`
and `cslc.amplitude_rmse_db_max = 4.0` live in `subsideo.validation.criteria`
and are never tightened toward the empirically-observed 0.79 / 3.77 dB
headroom (see §2.3 below for the M1 target-creep prevention argument).

### 1.4 Acceptable cross-version validation strategies

1. **Amplitude-based single-scene comparison** — the standard v1.0+ path.
   `compare_cslc` consumes per-burst HDF5 outputs and returns an amplitude
   correlation + RMSE-in-dB pair. Version-independent because the magnitude is
   the modulus of the complex value and is preserved (up to mantissa
   truncation) under sub-pixel kernel-driven phase differences.
2. **Self-consistency validation on our own chain** — Phase 3 CSLC
   self-consistency (`run_eval_cslc_selfconsist_{nam,eu}.py`) and Phase 4 DISP
   self-consistency adopt this strategy. 14 sequential 12-day IFGs internal to
   our chain are coherence-valid even if a single-scene comparison against an
   OPERA CSLC produced from a different isce3 version would not be coherent.
3. **Time-series scientific equivalence** — compare displacement velocity from
   our CSLCs against velocity from OPERA's CSLCs across the same epoch pair
   (Phase 4 DISP cross-chain scope, NOT Phase 3 single-chain scope). Two
   internally-consistent chains produce equivalent velocities under the same
   ground deformation even when their absolute phase references differ.

Phase-coherent single-scene cross-version comparison is **not on the
acceptable-strategies list** regardless of how many corrections are layered.
See §1.2.

---

## 2. Product-quality vs reference-agreement distinction

**TL;DR:** Every v1.1 matrix cell reports **two distinct categories of
measurement** that must not be conflated. *Product-quality* gates assess
whether our product is internally consistent. *Reference-agreement* gates
assess whether our product matches an *external* reference (OPERA, EGMS, JRC).
The categories use different criteria, move based on different evidence, and
render in structurally separate columns in `results/matrix.md`. They never
collapse into a single `.passed` boolean.

### 2.1 Definitions

| Category | Measures | Examples | When tightened |
|----------|----------|----------|----------------|
| **Product-quality** | Internal consistency of our chain against a target physical model | self-consistency coherence (Phase 3 CSLC, Phase 4 DISP), residual velocity on stable terrain, EGMS L2a stable-PS residual, DSWx F1 against JRC labels | When evidence shows our chain can consistently deliver a tighter bar (typically stack-length-dependent for InSAR self-consistency — see CSLC-V2-02 deferral) and an ADR justifies the change |
| **Reference-agreement** | Agreement between our chain and an external reference product | OPERA CSLC amplitude correlation/RMSE, OPERA DISP correlation/bias, EGMS L2a paired bias, OPERA DIST F1 vs operational v0.1 | Never. See §2.3. |

Dataclasses in `subsideo.validation.results` enforce the distinction at the
type level: `ProductQualityResult` and `ReferenceAgreementResult` are
structurally separate (no `.passed` collapse on a parent object); the
`matrix_writer.write_matrix` function renders them in distinct columns of
`results/matrix.md`. See `src/subsideo/validation/criteria.py` for the
`Criterion(type=Literal["BINDING", "CALIBRATING", "INVESTIGATION_TRIGGER"])`
field that sub-classifies how each criterion gates and how it is rendered.

### 2.2 Motivating example — the Iberian Meseta CSLC-S1 three-number row

`CONCLUSIONS_CSLC_SELFCONSIST_EU.md` (also referred to in the Phase 3 plan
frontmatter as `CONCLUSIONS_CSLC_EU.md`; both names refer to the same on-disk
document under the `SELFCONSIST_` prefix) §5 reports
**three independent numbers** for the Iberian/Meseta-North burst
`t103_219329_iw1`, none of which collapses into the others:

| Number | Category | Measurement | Criterion | Phase-3 verdict |
|--------|----------|-------------|-----------|-----------------|
| (a) | reference-agreement | OPERA CSLC amplitude `r` + `RMSE_dB` | `cslc.amplitude_r_min=0.6`, `cslc.amplitude_rmse_db_max=4.0` (BINDING) | not applicable for the EU AOI (OPERA L2 CSLC-S1 V1 is N.Am.-only) — for the SoCal anchor, see `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` §5.1 (`amp_r=0.982, amp_rmse_db=1.290`) |
| (b) | product-quality | self-consistency coherence `median_of_persistent` | `cslc.selfconsistency.coherence_min=0.7` (CALIBRATING) | calibration data point: Iberian/Meseta-North = 0.891 |
| (c) | product-quality | self-consistency residual `residual_mm_yr` (and the planned EGMS L2a stable-PS residual `egms_l2a_stable_ps_residual_mm_yr`) | `cslc.selfconsistency.residual_mm_yr_max=5.0` (CALIBRATING) — EGMS L2a residual tracked separately in CSLC-05 | calibration data point: Iberian/Meseta-North residual = +0.347 mm/yr (EGMS deferred — Bug 8) |

If (a) PASSes but (b) is low → the chain is geocoding correctly but has an
internal phase-temporal-stability problem. The honest response is NOT "relax
(b) because (a) PASSes" — that's the M4 goalpost-moving anti-pattern; see
§2.4.

If (a) is marginal (e.g. r = 0.62 against the 0.6 BINDING bar) but (b) is
strong (coh = 0.85) → the chain is self-consistent but geocodes differently
from OPERA. The honest response is NOT "tighten (a) to 0.8 now that we're so
close" — that's the M1 target-creep anti-pattern; see §2.3.

### 2.3 Target-creep prevention (M1)

Reference-agreement thresholds **must not tighten** based on the reference's
own score, even when per-cell reference-agreement dramatically outperforms the
criterion:

| Cell | Criterion | Measured | Anti-pattern response | Correct response |
|------|-----------|----------|-----------------------|------------------|
| RTC N.Am. | RMSE < 0.5 dB | 0.045 dB | Tighten to < 0.1 dB | Leave at < 0.5 dB. The 10× headroom is the reference's own quality, not a commitment we should inherit. |
| RTC EU (per burst) | RMSE < 0.5 dB | 0.04 – 0.1 dB | Tighten to < 0.15 dB | Leave at < 0.5 dB. See RTC-02 explicit anti-tighten clause. |
| CSLC amplitude (SoCal) | r > 0.6 | 0.79 (v1.0) / 0.982 (Phase 3 first epoch) | Tighten to r > 0.75 | Leave at r > 0.6. Tightening locks us to OPERA's interpolation kernel bias as the ceiling (see §1.1). |

`subsideo.validation.criteria` enforces this in code: every criterion is a
`@dataclass(frozen=True)` `Criterion`, so tightening requires a code-level PR
diff that an ADR or upstream-spec link must justify. `matrix_writer` echoes
the criterion threshold alongside the measured value in every cell so drift is
visible in git diffs of `results/matrix.md`. The reference-agreement threshold
must not be tightened — `must not be tightened` is the rule, full stop.

### 2.4 Goalpost-moving prevention (M4)

Product-quality thresholds **must not relax** based on the measured value,
even when a known-difficult cell lands just below the bar:

| Cell | Criterion | Measured | Anti-pattern response | Correct response |
|------|-----------|----------|-----------------------|------------------|
| DSWx EU (any AOI) | F1 > 0.90 | 0.87 | Relax to F1 > 0.85 | Leave at F1 > 0.90. Report "FAIL with named ML-replacement upgrade path" per the DSWX-07 discipline. |
| CSLC self-consistency (SoCal/Mojave/Iberian) | coh > 0.7 | 0.68 (hypothetical; observed values are higher) | Relax to coh > 0.6 | Apply the CALIBRATING discipline: report the measurement, not a PASS/FAIL verdict. The gate METRIC may change (CONTEXT D-04 escape valve — change `gate_metric_key`, not `threshold`) but the VALUE stays. |
| DISP velocity (any AOI) | bias < 3 mm/yr | 4.2 mm/yr | Relax to bias < 5 mm/yr | Leave at bias < 3 mm/yr. Report FAIL with attribution work (Phase 4 DISP ramp-attribution section, deferred). |

Product-quality thresholds **must not be relaxed** to clear a difficult-but-real
FAIL. An honest FAIL with a named upgrade path is more useful than a PASS at a
moved goalpost.

### 2.5 First-rollout CALIBRATING discipline (M5 + GATE-05)

Every product-quality gate introduced in v1.1 ships as **CALIBRATING** with
`binding_after_milestone='v1.2'` on its `Criterion` registry entry, and
requires ≥ 3 measured data points before it may be promoted to BINDING:

- CSLC self-consistency: SoCal + Mojave/Coso-Searles + Iberian/Meseta-North =
  3 calibration data points (this milestone — Phase 3 CSLC-03/04/05).
- DISP self-consistency: SoCal + Bologna = 2 data points (Phase 4); the third
  data point (a third AOI to be selected during Phase 4 planning) is required
  before the gate may bind.

CALIBRATING cells render italicised in `results/matrix.md` per Phase 1
D-03 / GATE-04. The `binding_after_milestone` field on the `Criterion`
dataclass prevents the M6 perpetual-CALIBRATING anti-pattern: at v1.2 start,
`make eval-all` refuses to run unless every CALIBRATING gate either flips to
BINDING or has an ADR documenting why the calibration window extends.

### 2.6 Cross-reference to other sections

| Distinction aspect | Future section (deferred per D-15) |
|--------------------|-----|
| DISP ramp-attribution (reference-agreement diagnostic depth) | Phase 4 will append (PHASS N.Am./EU re-runs as authoritative evidence) |
| DSWE F1 ≈ 0.92 architectural ceiling (product-quality interpretation) | Phase 5 or 6 will append (DSWX-07 named ML upgrade path is the authoritative evidence) |
| Cross-sensor precision-first framing (OPERA DIST vs EFFIS) | Phase 5 will append |
| OPERA frame selection by exact UTC hour (reference-agreement plumbing) | Phase 4 harness-first discipline will document |

(These sections are appended by later phases per CONTEXT D-15 append-only
policy. Phase 3 owns only §1 + §2 in this document; no stub headings for
later sections are pre-created.)

---
