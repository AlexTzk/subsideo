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

## Table of Contents

1. [CSLC cross-version phase impossibility](#cross-version-phase)
2. [Product-quality vs reference-agreement distinction](#pq-vs-ra)
3. [DISP comparison-adapter design — multilook method choice](#multilook-method)
4. [DIST-S1 Validation Methodology](#dist-methodology)
5. [DSWE F1 ceiling, held-out Balaton, and threshold-module design](#dswe-recalibration-methodology)
6. [OPERA frame selection by exact UTC hour + spatial footprint](#opera-utc-frame-selection)
7. [Cross-sensor comparison — precision-first framing (OPERA DIST vs EFFIS)](#cross-sensor-precision-first)
8. [ERA5 tropospheric diagnostic](#era5-tropospheric-diagnostic)
9. [CSLC CALIBRATING-to-BINDING conditions](#cslc-calibrating-to-binding)
10. [EGMS L2a reference methodology and named-blocker pattern](#egms-l2a-reference-methodology)
11. [DISP ERA5/deramping/unwrapper diagnostics](#disp-era5-deramping-unwrapper-diagnostics)
12. [DISP deferred posture and v1.3 handoff](#disp-deferred-posture)

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

<a name="pq-vs-ra"></a>

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

### CSLC v1.2 binding proposal (Phase 8)

Phase 8 proposes promoting CSLC self-consistency with the same gate metric,
`median_of_persistent`, rather than swapping metrics to fit the observed rows.
The Phase 9 candidate threshold is coherence `>= 0.75`, paired with a
stable-terrain residual threshold `<= 2.0 mm/yr`. Those thresholds remain
product-quality gates: they measure internal phase stability and residual
velocity over stable terrain, while OPERA amplitude sanity and any external
reference comparison stay in the separate reference-agreement category.

The proposal is conservative relative to the v1.1 calibration points:
SoCal `median_of_persistent=0.887` and residual `-0.109 mm/yr`,
Mojave/Coso-Searles `0.804` and `+1.127 mm/yr`, and Iberian Meseta-North
`0.868` and `+0.347 mm/yr`. Phase 8 records the candidate threshold and
hardens the inputs; Phase 9 performs the final reruns and either promotes,
narrows, or blocks the BINDING gate based on regenerated AOI windows and
stable-mask diagnostics.

### 2.6 Cross-reference to other sections

| Distinction aspect | Future section (deferred per D-15) |
|--------------------|-----|
| DISP ramp-attribution (reference-agreement diagnostic depth) | Phase 4 landed the multilook-method ADR in §3 (this doc); ramp-attribution per-cell evidence lives in CONCLUSIONS_DISP_N_AM.md §13 + CONCLUSIONS_DISP_EU.md §13 |
| DSWE F1 ≈ 0.92 architectural ceiling (product-quality interpretation) | Phase 5 or 6 will append (DSWX-07 named ML upgrade path is the authoritative evidence) |
| Cross-sensor precision-first framing (OPERA DIST vs EFFIS) | §7 documents |
| OPERA frame selection by exact UTC hour (reference-agreement plumbing) | §6 documents |

(These sections were appended by their authoring phases per CONTEXT D-15 append-only policy. Phase 3 authored §1 + §2; §3 was appended by Phase 4; §§4–7 by Phases 5–6; §8 by Phase 10; §§9–12 by Phase 12.)

---

## 3. DISP comparison-adapter design — multilook method choice

<a name="multilook-method"></a>

**TL;DR:** `subsideo.validation.compare_disp.prepare_for_reference()` requires
an explicit `method=` argument selected from
`Literal["gaussian", "block_mean", "bilinear", "nearest"]`. Phase 4 eval scripts
pass `method="block_mean"` -- the conservative kernel that doesn't inflate
reference-agreement r through kernel artefact. Switching the kernel
post-measurement requires CONCLUSIONS-level documentation per the
criterion-immutability principle.

### 3.1 Problem statement

subsideo's native DISP velocity is at 5 m × 10 m posting (OPERA CSLC spec).
The two reference products it must compare against -- OPERA DISP-S1
(30 m × 30 m) and EGMS L2a PS (point cloud at PS coordinates) -- live on
different grids. Comparing requires multilooking subsideo's velocity onto the
reference grid. The multilook method is a comparison-adapter design choice
that materially changes the reported `correlation` and `bias_mm_yr` values
(PITFALLS P3.1 warning sign: r differs by > 0.03 when switching between
kernels on the same data).

Native production output stays at 5×10 m (DISP-05 + ROADMAP key decision
"Native CSLC/DISP resolution stays production default"). The adapter is
**validation-only** infrastructure -- it never writes back to the product
(Phase 4 D-17 + research ARCHITECTURE §3 placement rationale).

### 3.2 PITFALLS P3.1 argument — Gaussian σ=0.5×reference is physically consistent

PITFALLS P3.1 (`.planning/research/PITFALLS.md` §P3.1) argues that OPERA's
30 m DISP output is itself produced from multilooked interferograms with an
effective Gaussian smoothing kernel. Multilooking subsideo's 5×10 m output
to 30 m via `gaussian_filter(σ_pix = 15m / native_spacing)` then nearest-
sampling onto the reference grid is the apples-to-apples comparison: both
fields carry the same effective spatial-frequency content. Block-mean (the
"averaging" rasterio resampler) under-smooths by truncating high frequencies
discretely rather than rolling them off; bilinear smooths but blurs
discontinuities; nearest preserves sub-pixel offsets and aliases.

**The argument's strength:** kernel matching is the standard practice in
remote-sensing validation when the reference is itself a multi-look product
(SAR / hyperspectral / PSI). The physics of velocity-difference power
across spatial frequencies says that if our product and the reference both
carry the same low-pass response, the comparison r is the apples-to-apples
"how well do these chains agree at the comparison cell size" number.

### 3.3 FEATURES anti-feature argument — block_mean is the kernel-flattery floor

FEATURES (`.planning/research/FEATURES.md` lines 71 + 142-143 anti-feature
table) argues the inverse: kernel choice can inflate reported r because
each kernel rolls off velocity-difference power differently. Picking the
kernel that gives the highest r is a kernel-choice attack surface -- the
reported r in `results/matrix.md` becomes a function of "we picked the
nicest kernel" rather than "the chains agree at the comparison cell size."
Block-mean (`Resampling.average` in rasterio) is the conservative floor:
it matches what OPERA itself uses for its CSLC multilook, and its
high-frequency truncation is the most pessimistic of the four kernels for
reference-agreement r. Anyone arguing Gaussian gives a higher r can rerun
with `method="gaussian"`; we don't pre-commit to the optimistic kernel for
the published metric.

**The argument's strength:** as a milestone-publish artifact (not a paper),
the kernel choice that gives the lower-bound r is the one we ship as the
official number. The anti-feature framing names this trade-off explicitly
and resists the M1 target-creep anti-pattern (don't tighten OR relax
criteria based on the resulting measurement).

### 3.4 Decision: block_mean as the eval-script default

`subsideo.validation.compare_disp.prepare_for_reference()` accepts all four
kernels -- both arguments above are correct on their own terms; the choice
is a posture, not a science argument (see Phase 4 04-CONTEXT.md §Specifics).
The **eval-script default** is `block_mean` because:

1. **Floor behaviour** -- block_mean's reported r is the most pessimistic
   of the four. If we PASS at block_mean, we PASS at any kernel; if we FAIL
   at block_mean, the FAIL is unambiguous (not a kernel artefact).
2. **OPERA parity** -- OPERA's own multilook in the CSLC pipeline is a
   block-average. Same kernel = same effective smoothing = honest comparison
   of two block-averaged products.
3. **No goalpost-moving (M1)** -- switching to Gaussian post-measurement
   because it gives a higher r is exactly the M1 target-creep anti-pattern
   `criteria.py` is designed to prevent. A future PR titled "switch to
   Gaussian for higher r" would be self-evidently wrong.

The eval-script constant `REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] =
"block_mean"` lives at module top in both `run_eval_disp.py` and
`run_eval_disp_egms.py` (Phase 4 D-04, mirroring Phase 1 D-11
`EXPECTED_WALL_S` pattern). The supervisor AST-parses it; switching the
kernel requires a visible PR diff to the constant, not a silent runtime
change.

### 3.5 Constraint: kernel choice is comparison-method, not product-quality

The kernel choice is **a comparison-method decision**, NOT a product-quality
decision. **Native 5×10 m stays the production default** (DISP-05 in
REQUIREMENTS; ROADMAP key decision; Phase 4 D-17). The eval script's
`REFERENCE_MULTILOOK_METHOD` constant lives at module top so it's auditable
in the git diff (mirrors the Phase 1 D-11 `EXPECTED_WALL_S` pattern).
Switching kernels post-measurement requires:

1. A PR diff to the constant (visible in
   `git log --grep="REFERENCE_MULTILOOK_METHOD"`).
2. A CONCLUSIONS sub-section documenting the new kernel's measured r/bias
   and citing this §3.5 constraint.

There is no env-var override or CLI flag. The kernel is a published-artifact
parameter; it must be code-visible.

(For the alternative-kernel rerun e.g. `method="gaussian"` for kernel-
comparison study: it's deferred to the Unwrapper Selection follow-up
milestone per Phase 4 04-CONTEXT.md §Deferred. CONCLUSIONS may cite
"block_mean reference shows r=X; the same data with method='gaussian' would
yield r=Y" as a v1.2/v2 footnote.)

---

## 4. DIST-S1 Validation Methodology

<a name="dist-methodology"></a>

This section documents the methodological choices made by Phase 5 for the
DIST-S1 product family (N.Am. + EU). Per the Phase 5 scope amendment
(2026-04-25), §4.5 (config-drift gate semantics) is **deferred to v1.2**
alongside DIST-01 / DIST-02 / DIST-03 — the gate cannot be authored without
an operational reference to drift against, and OPERA `L3_DIST-ALERT-S1_V1`
returns empty in CMR as of writing (RESEARCH Probes 1 + 6).

### 4.1 Single-event F1 variance + block-bootstrap CI

DIST-S1 ships at 30 m posting; a single Aveiro-class event yields O(10^4–10^5)
classified pixels but the underlying detection units (burn-scar polygons + RTC
multilooked windows) are spatially correlated at scales of hundreds of metres.
A naive pixel-wise F1 over-counts independent samples and produces a
spuriously narrow confidence interval.

The block-bootstrap CI in `src/subsideo/validation/bootstrap.py`
(Hall 1985 — moving block bootstrap with PCG64 seed=0) addresses this. The
method partitions the per-event difference grid into spatially contiguous
blocks of side `DEFAULT_BLOCK_SIZE_M = 1000` (m) — large enough to
de-correlate adjacent burn-scar polygons under the Sentinel-1 12-day repeat —
and resamples blocks with replacement `DEFAULT_N_BOOTSTRAP = 500` times to
estimate the F1 distribution. Reported CIs are at `DEFAULT_CI_LEVEL = 0.95`.
Pixel size for the block-count math is `DEFAULT_PIXEL_SIZE_M = 30`.

These constants live as module-level attributes in `bootstrap.py` and are
written into `meta.json.bootstrap_config` (when populated) so a downstream
audit can re-evaluate the same data with different block sizes if the
correlation length is later revised. The seed is fixed (`DEFAULT_RNG_SEED = 0`)
so repeat runs of the same eval produce byte-identical CIs — this is the
reproducibility contract for the matrix.

The CI is the load-bearing pass/fail signal: a single F1 point estimate is
not actionable when the bootstrap distribution has a CI half-width comparable
to the threshold (e.g. F1 = 0.71 [0.55, 0.86] is qualitatively different
from F1 = 0.71 [0.69, 0.73] even though both have the same point estimate).
Phase 5 reports both the point estimate and the 95% CI in every per-event
row of the dist:eu cell.

### 4.2 EFFIS rasterisation choice (`all_touched=False` primary)

The EFFIS REST API (`api.effis.emergency.copernicus.eu/rest/2/burntareas/current/`,
adopted after both candidate WFS endpoints failed in Plan 05-02) returns
burnt-area perimeter polygons as GeoJSON Feature objects. The validation
pipeline must rasterise these onto the 30-m OPERA DIST grid for cell-wise
comparison.

`src/subsideo/validation/effis.py` performs a **dual rasterise**:

- **Primary**: `all_touched=False` — only pixels whose *centre* lies inside a
  burn-scar polygon are flagged as positive. This matches OPERA DIST-S1's own
  rasterisation convention (centre-of-pixel sampling against the burn polygon),
  which is what the DIST product effectively encodes when its high-resolution
  internal mask is downsampled to 30 m. CONTEXT D-17 records this as the
  binding choice for the per-event F1 numerator.

- **Diagnostic**: `all_touched=True` — every pixel touched by the polygon
  boundary is flagged. The intersection of the two rasters bounds the
  rasterisation-induced uncertainty: `all_touched=True` is the maximally
  permissive count, `all_touched=False` is the centre-only count. The two
  numbers are reported side-by-side in the per-event diagnostic so the user
  can judge whether a borderline F1 is rasterisation-limited.

The constant pinning the REST resource path is `EFFIS_LAYER_NAME =
"burntareas/current"` (was a WFS typename in the v1.0 plan; the REST pivot
is documented in `eval-dist_eu/effis_endpoint_lock.txt`).

### 4.3 EFFIS class-definition mismatch caveat

EFFIS reports burnt-area perimeters consolidated *post-event* (typically
days-to-weeks after the fire is extinguished). OPERA DIST-S1, in contrast,
detects active disturbance signal in the radar backscatter time series — it
flags pixels as *first-detection*, *provisional*, *confirmed*, *finished*
along the alert lifecycle.

PITFALLS P4.5 records the consequence: a pixel labelled
`GEN-DIST-STATUS = 5` (confirmed-fd-high) by DIST-S1 may correspond to an
EFFIS polygon dated 14 days *after* the DIST detection event. The two
references are *temporally consistent* (both indicate "fire happened in this
period") but *not class-equivalent*. Specifically:

- DIST-S1 flags wildfire **and** clear-cut **and** other surface
  disturbances; EFFIS is **fire-only**. (This is why Plan 05-07 substituted
  Spain Sierra de la Culebra for the originally-planned Romania 2022
  clear-cuts: clear-cuts have no EFFIS coverage so the per-event F1 would
  spuriously read 0.)
- The EFFIS polygon footprint is the *final extent* (cumulative burned
  area); the DIST-S1 footprint at any single post-date is the
  *snapshot-of-detection* extent. F1 is computed against the *cumulative*
  EFFIS polygon and the post-date DIST-S1 raster — meaning a low-recall
  result for an early post-date may simply reflect the fire still spreading,
  not a missed detection.

The chained_retry differentiator (DIST-07; aveiro Sept 28 → Oct 10 → Nov 15)
exercises this: each successive post-date should bring the DIST-S1 footprint
closer to the EFFIS final extent (recall increases monotonically), giving a
qualitative validation of the alert-promotion logic without requiring
EFFIS to be re-queried at intermediate dates.

### 4.4 CMR auto-supersede behaviour (DIST-04)

The N.Am. dist:nam matrix cell ships as DEFERRED in v1.1 because the OPERA
v0.1 DIST-S1 sample has no canonical CloudFront URL (Probe 1: notebook-recipe
regeneration only) and the operational `OPERA_L3_DIST-ALERT-S1_V1`
collection is empty in CMR (Probe 6 as of 2026-04-25). v1.2 will add the
full F1+CI pipeline once operational publishes.

Rather than freeze v1.1 with a stale "operational not available" assertion,
Plan 05-06 implements an **auto-supersede CMR probe** in
`run_eval_dist.py` Stage 0:

1. Every `make eval-dist-nam` invocation queries CMR for
   `OPERA_L3_DIST-ALERT-S1_V1` covering T11SLT 2025-01-21 ± 7 days
   (`earthaccess.search_data`).
2. **Empty result** (the expected v1.1 outcome) → write `metrics.json` with
   `cell_status='DEFERRED'`, `cmr_probe_outcome='operational_not_found'`.
3. **Non-empty result** (v1.2 trigger event) → archive any pre-existing
   `eval-dist/metrics.json` to `eval-dist/archive/v0.1_metrics_<mtime-iso>.json`
   per CONTEXT D-16, then raise `NotImplementedError` pointing at v1.2.
4. **Network/auth failure** → `cmr_probe_outcome='probe_failed'`, cell still
   DEFERRED but with a different cause-code in the matrix render.

The matrix render branch in `matrix_writer.py` reads `cmr_probe_outcome`
verbatim and renders `DEFERRED (CMR: operational_not_found)` (or
`probe_failed`) — the matrix surface always reflects the most recent probe
outcome. When v1.2 lands and operational appears, the
`NotImplementedError` is the unambiguous re-plan signal: the user runs
`/gsd:plan-phase 5 --gaps` and the v1.2 milestone activates the full
pipeline. The archival hook (`eval-dist/archive/`) preserves the v1.1
deferred-state record for audit purposes — it is not overwritten by v1.2.

This gives v1.1 a **forward-compatible** deferral: the cell automatically
advances when operational publishes, with no manual repointing of scripts
or manifest entries. The unit-test suite at
`tests/unit/test_run_eval_dist_cmr_stage0.py` exercises all three outcome
branches (operational_not_found, probe_failed, operational_found) so the
contract is regression-protected.

### 4.5 Config-drift gate semantics — DEFERRED to v1.2

**Not authored in v1.1.** The config-drift gate compares the active
`dist_s1` algorithm config against the config the operational reference
was generated with; without an operational reference, no drift can be
detected. v1.2 will land §4.5 alongside the operational F1+CI pipeline.

---

## 5. DSWE F1 ceiling, held-out Balaton, and threshold-module design

<a name="dswe-recalibration-methodology"></a>

**TL;DR:** The DSWE-family F1 "0.92 ceiling" claim in BOOTSTRAP_V1.1.md was a
misattribution (OSW class accuracy misread as F1). Path (c) from Plan 06-01 PROTEUS ATBD
probe succeeded: OPERA Cal/Val published F1_OSW mean = 0.8786 over 52 scenes. Held-out
Balaton F1 IS the OFFICIAL EU matrix-cell value per BOOTSTRAP §5.4 — fit-set mean F1 cannot
collapse the matrix verdict. The shoreline 1-pixel buffer is applied uniformly in BOTH grid
search AND final reporting (single source of truth). LOO-CV gap < 0.02 acceptance gates the
recalibration against overfit (10-fold leave-one-pair-out per B1 fix). The threshold module
uses a frozen+slots dataclass with inline provenance; YAML/runtime-config explicitly
forbidden per DSWX-05.

### 5.1 DSWE F1 ceiling citation chain

Per Plan 06-01 PROTEUS ATBD probe
(`./planning/milestones/v1.1-research/dswx_proteus_atbd_ceiling_probe.md`), **Path (c)
SUCCEEDED** (OPERA-Cal-Val/DSWx-HLS-Requirement-Verification repository). The following
replaces all "DSWE F1 ≈ 0.92 architectural ceiling" language from earlier drafts:

**OPERA DSWx-HLS v1.0 Cal/Val baseline (not a "ceiling"):** The official OPERA Cal/Val
verification (source: OPERA-Cal-Val/DSWx-HLS-Requirement-Verification, N=52 globally
distributed scenes, 100-bootstrap validation against Planet-based labels,
`out/verification_stats_agg/100-trials_conf-classes-none_sample-from-val/metrics.csv`) reports:

| Metric | Value |
|--------|-------|
| Open Surface Water (OSW) F1 mean | **0.8786 ± 0.08** (range: 0.43–1.00) |
| OSW class accuracy mean | 91.6% ± 10.6% (OPERA requirement: > 80%) |
| Partial Surface Water (PSW) F1 mean | 0.5843 (N=45 scenes) |
| Not Water (NW) F1 mean | 0.9570 |
| Binary Water Accuracy | 96.1% mean |

**The "0.92 ceiling" phrase in BOOTSTRAP_V1.1.md is incorrect:** the 0.92 figure corresponds
to mean OSW class accuracy (91.6%), not F1. PITFALLS P5.3 explicit warning sign: "0.92
architectural ceiling" is a game-of-telephone citation (class accuracy misattributed as F1).

The Phase 6 F1 > 0.90 gate (`criteria.py:188` `dswx.f1_min = 0.90`) is ABOVE the published
Cal/Val OSW mean F1 (0.8786). This makes the Phase 6 gate a project-level ambition, not a
literature claim. The gate is **isolated** from the ceiling claim per PITFALLS P5.3 explicit
isolation strategy: the gate stays at 0.90 regardless of where the ceiling sits.

Path (d) own-data fallback was not required. If a future PROTEUS ATBD release provides
additional citable F1 numbers, this §5.1 wording revises in a future v1.x milestone — that
is a methodology-doc edit only, not a `criteria.py` edit.

### 5.2 Held-out Balaton vs fit-set methodology

Per BOOTSTRAP §5.4 + CONTEXT D-13: the OFFICIAL EU matrix-cell value is the **held-out
Balaton F1**, NOT the fit-set mean F1. PITFALLS P5.1 explicit:

> Balaton F1 < 0.90, report FAIL — not "fit-set F1 passed."

Plan 06-06 holds Balaton truly out of the 5-AOI fit-set construction; the 12 (AOI, scene)
pairs in the grid search are 5 fit-set AOIs × 2 wet/dry + Balaton wet/dry, but only the 10
fit-set pairs participate in gridpoint F1 aggregation (B1 fix corrects an earlier 12-fold
conflation). After grid search converges to a joint best gridpoint via fit-set-only F1,
Balaton is scored once at the joint best gridpoint — that single number is the gate.

Fit-set mean F1 + per-AOI F1 breakdown are reported alongside in `eval-dswx/metrics.json`
as `fit_set_mean_f1` and `per_aoi_breakdown` — diagnostics, NOT the gate.

**Phase 6 outcome:** The recalibration did not converge (fit_set_mean_f1=0.2092; BLOCKER
after 3 iterations; HLS→S2 L2A spectral transfer gap). The Balaton held-out F1 was computed
against PROTEUS defaults (THRESHOLDS_EU unchanged): F1 = 0.8165 (shoreline-excluded) vs
F1 = 0.7957 (full pixels; no buffer). The shoreline buffer accounts for the +0.021 gap —
confirming JRC labelling noise at water/land boundaries as expected (PITFALLS P5.2).

### 5.3 Shoreline 1-pixel buffer rationale

Per **PITFALLS P5.2** (W4 fix cross-reference): JRC Monthly History has documented
commission accuracy 98–99% and omission accuracy 74–99% (Pekel et al. 2016,
*High-resolution mapping of global surface water and its long-term changes*, Nature
540:418–422; see also `.planning/research/PITFALLS.md §P5.2`). Specifically:

- **Land-in-shadow classified as water** (mountain shadow, deep urban canyon shadow).
  Alpine valley AOIs (Garda) most affected.
- **Light clouds over water classified as land.** Atlantic estuary AOIs (Tagus) in
  variable-weather months affected.
- **Shoreline pixels ambiguous.** JRC uses 30 m Landsat pixels; a pixel 50% water / 50%
  shore gets classified one way but the ground truth is mixed.

The shoreline 1-pixel buffer (`scipy.ndimage.binary_dilation` XOR-of-water-and-non-water-
dilations on JRC native 4326 grid; reprojected to S2 UTM via `Resampling.nearest`) excludes
these structurally-ambiguous boundary pixels from the F1 evaluation. CONTEXT D-16 mandate:
applied UNIFORMLY in BOTH the grid search (Plan 06-06 Stage 4) AND final reporting (Plan
06-07 Task 1 + Plan 06-05 N.Am. positive control). Single source of truth; auditable via
`f1_full_pixels` diagnostic stamped alongside the gate `f1` value.

The buffer reduces false negatives at the shoreline (DSWx classifies the pixel as water; JRC
labels it as land due to 50% shore) and false positives (DSWx classifies as non-water; JRC
labels as water). The decision is methodologically conservative — F1 is computed on pixels
where both classifiers can confidently agree.

**Phase 6 evidence:** Balaton 2021-07, 187,556 pixels excluded (5.6% of valid comparison
pixels); F1 gate = 0.8165 vs F1_full = 0.7957 (+0.021). Cross-references: PITFALLS §P5.2
commission/omission accuracy bounds from Pekel et al. 2016 Nature 540:418–422.

### 5.4 LOO-CV overfit detection (gap < 0.02; B1 10-fold leave-one-pair-out)

Per PITFALLS P5.1: a 3-parameter joint grid search over WIGT × AWGT × PSWT2_MNDWI on 10
(AOI, season) fit-set pairs has 8400 combinations; with effective spatial autocorrelation
reducing 14M-pixel sample to ~140K independent samples, the multimodal F1 landscape has
multiple local optima. Standard overfitting symptom: fit-set mean F1 = 0.91; held-out F1 =
0.85; train/test gap = 0.06.

DSWX-06 acceptance gate: **gap = fit_set_mean_f1 − loocv_mean_f1 < 0.02**.

Plan 06-06 Stage 7 implements LOO-CV post-hoc on the joint best gridpoint via
**leave-one-pair-out** (B1 fix; 10 folds, NOT 12 nor 5):

1. For each of the 10 (aoi, season) pairs in the fit set: refit thresholds on the remaining
   9 pairs; pick the LOO-best gridpoint per fold.
2. Score the left-out pair at the per-fold refit_best.
3. Average across 10 folds = `loocv_mean_f1`.

The B1 fix corrects an earlier writing error in CONTEXT D-14 ("rotate 12 times") that
conflated 12 fit-set+held-out total pairs with the actual 10 fit-set folds. Leave-one-pair-
out preserves the fit-set's wet/dry seasonal signal (each fold's refit set retains the
held-out AOI's other-season pair), whereas leave-one-AOI-out (5 folds) collapses both
seasons of the held-out AOI together and loses that signal.

**Phase 6 outcome:** LOO-CV was not executed because the recalibration did not converge to
a fit-set threshold set (fit_set_mean_f1=0.2092 < 0.5 hard-stop; BLOCKER after Iteration 3).
The LOO-CV gap is NaN in `eval-dswx/metrics.json` — this is NOT a gap violation; it is
vacuously met (no recalibration to overfit against). The DSWX-06 acceptance gate applies
when a valid recalibration lands; v1.2 EU recalibration must gate on loocv_gap < 0.02 before
overwriting THRESHOLDS_EU.

If `loocv_gap >= 0.02`: Plan 06-06 Stage 8 hard-gates with `cell_status='BLOCKER'` +
`loocv_gap_violation=True` + `sys.exit(2)`. Resolution paths per CONTEXT D-14 user
CHECKPOINT 2: (a) expand fit-set AOI count by substituting an alternate biome AOI; (b)
accept the overfit-flagged calibration with documented rationale; (c) halt Phase 6 with
FAIL + named_upgrade_path='fit-set quality review'.

### 5.5 Threshold module + region selector design

Per DSWX-05 + CONTEXT D-09..D-12: recalibrated thresholds live in
`src/subsideo/products/dswx_thresholds.py` as a **frozen+slots dataclass** `DSWEThresholds`
carrying the 3 grid-tunable thresholds (WIGT, AWGT, PSWT2_MNDWI) plus 9 provenance fields
(grid_search_run_date, fit_set_hash, fit_set_mean_f1, held_out_balaton_f1, loocv_mean_f1,
loocv_gap, notebook_path, results_json_path, provenance_note). Two singleton instances:

- `THRESHOLDS_NAM`: PROTEUS defaults (WIGT=0.124, AWGT=0.0, PSWT2_MNDWI=−0.5) with
  sentinel provenance values (`grid_search_run_date='1996-01-01-PROTEUS-baseline'`,
  `fit_set_hash='n/a'`, F1 fields = NaN).
- `THRESHOLDS_EU`: Phase 6 grid-search output placeholder (W1 sentinel-anchor slicing
  in `dswx_thresholds.py`). Under v1.1 honest-BLOCKER closure, THRESHOLDS_EU retains
  PROTEUS defaults with `fit_set_hash=''` (empty) and `fit_set_mean_f1=NaN`. The W5 Stage
  0 pre-check in `run_eval_dswx.py` warns (not asserts) when `fit_set_hash` is empty,
  allowing the Balaton eval to proceed with PROTEUS defaults while clearly documenting the
  recalibration-deferred state.

Region selection at `run_dswx` call time:

```python
# subsideo/config.py
class Settings(BaseSettings):
    dswx_region: Literal["nam", "eu"] = "nam"  # SUBSIDEO_DSWX_REGION env-var

# subsideo/products/types.py
@dataclass
class DSWxConfig:
    region: Literal["nam", "eu"] | None = None  # config-time override

# subsideo/products/dswx.py
def run_dswx(config: DSWxConfig) -> DSWxResult:
    settings = Settings()
    region = config.region or settings.dswx_region  # config > env > default 'nam'
    thresholds = THRESHOLDS_BY_REGION[region]
    diagnostic = _compute_diagnostic_tests(..., thresholds=thresholds)
```

YAML / runtime file I/O is explicitly forbidden per DSWX-05 (REQUIREMENTS.md): provenance
flows as dataclass attributes, grep-discoverable, immutable (slots=True), git-diff-visible
at PR review time.

The decomposition of `_compute_diagnostic_tests` into public `compute_index_bands`
(band-driven, threshold-free) + `score_water_class_from_indices` (threshold-driven, takes
pre-computed IndexBands) per CONTEXT D-05 is the architectural enabler for Plan 06-06's
8400-gridpoint grid search to run in ~25–45 min on M3 Max instead of ~6 hr — the index
bands are computed ONCE per (AOI, scene) and cached as float32 .npy; the inner threshold
loop scores the cached arrays via `score_water_class_from_indices` 8400 times per pair.

W5 fix (Plan 06-07 Stage 0): `run_eval_dswx.py` warns when `THRESHOLDS_EU.fit_set_hash =
''` immediately after `_mp` + `credential_preflight`, BEFORE any pipeline work. Catches the
Plan-06-06-not-yet-landed case loudly rather than silently producing a Balaton F1 against
PROTEUS placeholders that would be indistinguishable from the v1.0 baseline F1=0.7957.
Under v1.1 honest-BLOCKER closure the warning fires; under v1.2 successful recalibration
the warning is silent (non-empty fit_set_hash).

---

## 6. OPERA frame selection by exact UTC hour + spatial footprint

<a name="opera-utc-frame-selection"></a>

**TL;DR:** When `asf-search` returns multiple candidate OPERA frames for the same burst, the correct frame is identified by matching the exact acquisition UTC hour (not just date) plus spatial footprint overlap — not by selecting the first result. Any eval script that skips this step produces invalid reference-agreement numbers.

### 6.1 Structural argument — why UTC hour matters

OPERA processes Sentinel-1 acquisitions burst-by-burst. A given MGRS tile or burst footprint may be covered by two distinct Sentinel-1 passes within the same calendar day: one ascending (typically late-night UTC) and one descending (typically morning UTC). These passes differ in:

- **Look geometry** — ascending and descending passes illuminate the same ground from opposite look angles; backscatter and displacement projections are geometry-dependent.
- **Orbit reference frame** — ascending and descending passes belong to different relative orbit tracks; mixing them contaminates any cross-track comparison.
- **Sensing timestamp** — the burst UTC sensing time determines which OPERA frame corresponds to the source SLC. Two frames with the same date but different UTC hours are different data products.

`asf-search` returns all frames covering a spatial query; without UTC-hour filtering, the first result may correspond to a different pass than the source SLC used to generate the subsideo product. Comparing against the wrong OPERA frame produces a reference-agreement number that reflects pass-geometry mismatch, not algorithm agreement.

### 6.2 Policy statement

**Any eval script that selects an OPERA reference without UTC-hour + footprint matching is producing invalid reference-agreement numbers.** A pull request that removes or bypasses `select_opera_frame_by_utc_hour()` from an eval script MUST explain in its description why the source SLC and all candidate OPERA frames share a unique UTC-hour + footprint match before merge. Adding a date-only filter or a simple `.first()` on the asf-search result is not a valid substitute — it is the exact pattern this function was written to prevent.

The spatial footprint criterion catches a second failure mode: an OPERA frame may share the same UTC sensing hour as the source SLC but cover a different geographic extent (adjacent burst, adjacent frame). Footprint overlap (intersection area > threshold) is required alongside the UTC-hour match.

### 6.3 Code pointer

`subsideo.validation.harness.select_opera_frame_by_utc_hour()` (`src/subsideo/validation/harness.py`):

```python
def select_opera_frame_by_utc_hour(
    sensing_datetime: datetime,
    frame_metadata: Sequence[dict[str, Any]],
    *,
    tolerance_hours: float = 1.0,
) -> dict[str, Any]:
```

The function accepts a query `sensing_datetime` (typically the source SLC sensing time), a list of candidate frames from `asf-search`, and a `tolerance_hours` window (default 1.0 h). It raises `ValueError` when zero or multiple frames match within the window — the ambiguous-match case is an error, not a silent default. All Phase 2–6 eval scripts that perform OPERA reference selection call this function.

### 6.4 Diagnostic evidence

`CONCLUSIONS_RTC_EU.md` §5 documents the Phase 2 multi-pass disambiguation for burst `T168-356151-IW1` (alpine regime, Austria). The `asf-search` result set for the Lake Achen area on 2021-09-04 returned two candidate frames — one ascending at 05:11 UTC and one descending at 16:42 UTC. Without UTC-hour filtering, the descending-pass frame would have been selected (it returned first in the asf-search result list); the ascending-pass frame — the one geometrically consistent with the source SLC — would have produced `r = 0.97, RMSE = 0.09 dB`. The descending-pass comparison produced `r = 0.41, RMSE = 2.3 dB` — an apparent FAIL caused entirely by look-geometry mismatch, not algorithm error. `select_opera_frame_by_utc_hour()` correctly selected the ascending-pass frame.

---

## 7. Cross-sensor comparison — precision-first framing (OPERA DIST vs EFFIS)

<a name="cross-sensor-precision-first"></a>

**TL;DR:** EFFIS reports confirmed *final* burnt-area perimeters days-to-weeks post-event; DIST-S1 flags *first-detection* active disturbance signal. A high-precision / low-recall result is scientifically expected — it is not a system failure. Cross-sensor eval results with recall < 0.50 but precision > 0.70 are reported as "precision-first constraint satisfied" rather than unqualified FAIL.

### 7.1 Structural argument — temporal class-definition mismatch

The DIST-S1 and EFFIS products answer different questions:

- **DIST-S1** detects a change in the SAR backscatter time series at first-detection time. The product is designed for rapid alert — it flags the pixel as `GEN-DIST-STATUS = 2` (provisional) as soon as the backscatter change exceeds the algorithm threshold, days before the fire is extinguished.
- **EFFIS** (and its REST successor, `api.effis.emergency.copernicus.eu/rest/2/burntareas/current/`) reports the *post-event cumulative perimeter* — the final consolidated burnt-area polygon assembled from satellite optical imagery collected days-to-weeks after the fire is extinguished.

This creates a structural asymmetry:

1. **Recall is architecturally suppressed** when comparing DIST-S1 at a single post-date against the EFFIS final extent. If the fire was still spreading on the DIST-S1 post-date, the DIST-S1 footprint is a partial snapshot; the EFFIS polygon is the cumulative final record. Recall = DIST-S1 detections / EFFIS final area will be < 1 by construction for any fire still spreading.

2. **Precision is the load-bearing metric** in this cross-sensor comparison. A DIST-S1 pixel that EFFIS later confirms as burnt-area is a true positive. DIST-S1 true-positive rate (precision) against EFFIS is a valid signal for "did DIST-S1 correctly identify real fire?" even when recall is low.

3. **EFFIS is fire-only**; DIST-S1 flags wildfire + clear-cut + other surface disturbances. This prevents Romania-style clear-cut events from being evaluated via EFFIS (see Phase 5 Spain Sierra de la Culebra substitution rationale in ROADMAP Phase 5 scope amendment).

### 7.2 Policy statement

**Cross-sensor evaluation results that show recall < 0.50 but precision > 0.70 MUST be reported as "precision-first constraint satisfied; recall gap attributed to temporal class-definition mismatch (EFFIS final extent vs DIST first-detection)" — not as unqualified FAIL.** A pull request that labels this result as "DIST-S1 EU FAIL" without the precision-first caveat fails the MEL-06 anti-reporting-collapse check.

The exception: if precision itself collapses (precision < 0.50), the result is an unqualified FAIL regardless of the temporal class-definition mismatch — low precision means DIST-S1 is flagging pixels EFFIS never confirms as burnt-area.

The chained-retry differentiator (DIST-07; aveiro Sept 28 → Oct 10 → Nov 15) provides the qualitative test: recall should increase monotonically across post-dates as the fire progresses toward EFFIS final extent. A non-monotonic recall sequence is a signal worth investigating, not a precision-first attribution.

### 7.3 Code pointer

`src/subsideo/validation/effis.py` implements the dual rasterise that operationalises the precision-first framing:

- `all_touched=False` (primary gate): only pixels whose centre lies inside the EFFIS burn-scar polygon are flagged. This is the conservative count used for the official F1 numerator.
- `all_touched=True` (diagnostic): every pixel touched by the polygon boundary is flagged. The ratio between the two counts bounds the rasterisation-induced uncertainty at the polygon edge.

The `EFFIS_LAYER_NAME = "burntareas/current"` REST resource path is the post-event consolidated perimeter source. See also the eval-dist_eu/effis_endpoint_lock.txt committed artifact (Plan 05-02) for the endpoint lock rationale (both WFS candidates failed; REST adopted as primary).

### 7.4 Cross-reference to §4.3

Section 4.3 of this document ("EFFIS class-definition mismatch caveat") provides the implementation-level evidence for the temporal mismatch described here. §4.3 documents the specific Phase 5 findings (Aveiro chained-retry monotonicity, Spain Sierra de la Culebra substitution, EMSR686 Evros activation). §7 is the methodology-level framing that §4.3 evidence supports: the precision-first policy statement in §7.2 applies to any future DIST-S1 cross-sensor comparison against EFFIS or similar post-event perimeter products, not only to the three Phase 5 events.

## 8. Phase 10 DISP ERA5 Diagnostic

<a name="era5-tropospheric-diagnostic"></a>

### ERA5 tropospheric diagnostic

ERA5 is a **diagnostic** input for Phase 10 DISP ramp attribution, not a new default baseline by itself. A cell may only promote ERA5-on into a required baseline when it shows at least two independent improvement signals across reference agreement and ramp behavior, such as improved correlation, lower absolute bias/RMSE, and reduced ramp magnitude without degrading product-quality evidence.

The Phase 10 SoCal and Bologna runs both completed with ERA5 enabled and schema-valid `DISPCellMetrics` sidecars. Neither cell met the two-signal rule: SoCal reference agreement worsened, while Bologna remained effectively unchanged. Therefore Phase 11 keeps the v1.1 global candidate order instead of requiring ERA5-on for all unwrapper candidates.

`inconclusive_narrowed` is a human-facing narrative label only. It may be useful in conclusions when ERA5, orbit coverage, DEM diagnostics, and terrain diagnostics reduce the plausible-cause set, but it must not collapse schema categories or become a hidden pass/fail bit.

Product-quality, reference-agreement, and ramp-attribution remain separate:

| Evidence stream | Meaning | Phase 10 example |
|-----------------|---------|------------------|
| Product-quality | Internal consistency on stable terrain | stable residual can be small even when persistent coherence is 0.000 |
| Reference-agreement | External OPERA/EGMS agreement | both ERA5-on cells still fail `r > 0.92` and bias `< 3 mm/yr` |
| Ramp-attribution | Per-IFG planar-ramp behavior and cause hints | both cells remain `inconclusive` despite ERA5-on |

When neither DISP cell meets the ERA5 two-signal rule, the Phase 11 fallback order remains: "SPURT native first, then PHASS deramping, then tophu/SNAPHU, then 20 x 20 m fallback."

---

## 9. CSLC CALIBRATING-to-BINDING conditions

<a name="cslc-calibrating-to-binding"></a>

**TL;DR:** A CSLC product-quality gate may be promoted from CALIBRATING to BINDING when both signal thresholds are met on all active AOIs with no named blocker outstanding. If a named blocker exists, the gate stays BINDING BLOCKER with structured evidence until the per-AOI unblock condition is met.

### 9.1 Problem statement (ADR-style)

The Phase 1 CALIBRATING discipline (§2.5 of this document) requires ≥ 3 measured data points before promotion and sets `binding_after_milestone='v1.2'` on CSLC self-consistency criteria. Phase 8 proposed BINDING thresholds, and Phase 9 executed reruns against those thresholds. Both N.Am. and EU CSLC cells landed as BINDING BLOCKER in Phase 9, not BINDING PASS. This section documents the promotion rule, the named-blocker definition, and the per-AOI conditions that must be met before a future phase can promote.

### 9.2 Two-signal promotion rule

A CSLC gate promotion from CALIBRATING to BINDING requires ALL of the following to be true simultaneously:
1. All active AOIs produce `median_of_persistent >= 0.75` (Phase 8 proposed threshold; conservative relative to observed values: SoCal=0.887, Mojave/Coso-Searles=0.804, Iberian=0.868).
2. All active AOIs produce `stable_terrain_residual_mm_yr <= 2.0` (Phase 8 proposed threshold; conservative: SoCal=-0.109, Mojave=+1.127, Iberian=+0.347).
3. No named blocker is outstanding for any active AOI.
4. Regenerated sidecars (not stale v1.1 cache reads) back the threshold comparison.

If condition (3) is not met, the gate renders as BINDING BLOCKER with the blocker name in the matrix cell (e.g., `required_aoi_binding_blocker (Mojave)`). BINDING BLOCKER is not CALIBRATING — it represents structured evidence that the threshold is achievable but an external dependency is blocking the final measurement.

### 9.3 Named-blocker definition

A named blocker is an evidence-backed reason why a required measurement cannot be produced, where the reason is external to the algorithm under test. Named blockers must include:
- Blocker name (a unique string e.g., `required_aoi_binding_blocker`)
- Cell and AOI affected
- Evidence of the blocking condition (API failure log, frame-search result, stable-PS count)
- Dated unblock condition (what must change + in which milestone)

Named blockers are NOT "the measurement failed" — they are "the measurement cannot yet be produced for this specific external reason." A FAIL on coherence is not a named blocker; it is a BINDING FAIL.

### 9.4 Per-AOI unblock conditions (v1.2 state)

| AOI | Blocker name | Blocking condition | Unblock condition | Target milestone |
|-----|-------------|-------------------|-------------------|-----------------|
| Mojave/Coso-Searles (N.Am.) | `required_aoi_binding_blocker` | No reliable OPERA CSLC frame match for the Coso-Searles fallback burst in the regenerated Phase 9 frame search | A valid OPERA CSLC frame match is found and amplitude sanity is populated with measured r and RMSE | v1.3 |
| Iberian (EU) | `required_aoi_binding_blocker` | EGMS L2a third number unavailable: EGMStoolkit programmatic download gap means the stable-PS residual for the Iberian burst cannot be populated (§10 documents the tooling state) | A programmatic EGMS L2a download path succeeds AND stable-PS residual is populated for the Iberian burst | v1.3 |

### 9.5 Future promotion guidance

When a future phase resolves both per-AOI blockers above: regenerate metrics sidecars against the Phase 8/9 thresholds, confirm no new blockers exist, update `criteria.py` to flip `type='CALIBRATING'` to `type='BINDING'` for the CSLC self-consistency coherence and residual criteria, and regenerate the results matrix. The promotion must be a single atomic commit with regenerated sidecars + criteria.py change + matrix update. No silent criteria drift.

---

## 10. EGMS L2a reference methodology and named-blocker pattern

<a name="egms-l2a-reference-methodology"></a>

**TL;DR:** EGMS L2a per-burst PS point clouds are the EU DISP reference. The spatial join uses `prepare_for_reference(method='block_mean')` discipline at PS coordinates. Named blockers for EGMS-dependent cells must document the EGMStoolkit tooling state, the token/credential gap, and the stable-PS count as of the blocking run.

### 10.1 EGMS L2a as EU reference

EGMS L2a is the European Ground Motion Service Level 2a per-burst PS product distributed by Copernicus Land Monitoring Service (release `2018_2022`, EPSG:3035). It provides per-track, per-orbit PS velocities with mm/yr precision calibrated against a stable reference set. For EU DISP cells, it is the primary reference-agreement target (§5.2 in `CONCLUSIONS_DISP_EU.md` §5).

The comparison pipeline:
1. Load EGMS L2a CSVs via EGMStoolkit, reprojecting ETRS89-LAEA (EPSG:3035) easting/northing to WGS84.
2. Build a geopandas point layer, clip to raster bounds, sample subsideo LOS velocity at each PS coordinate via `rasterio.DatasetReader.sample` (nearest-neighbour).
3. Convert subsideo velocity rad/yr → mm/yr using `SENTINEL1_WAVELENGTH_M = 0.05546576`.
4. Compute Pearson r, bias, RMSE over the finite paired subset.

The `prepare_for_reference(method='block_mean')` constant governs the multilook kernel per the §3 multilook ADR, even though form (c) point-sampling does not apply a spatial kernel per se — the constant documents the cell's multilook discipline for matrix-row consistency with SoCal.

### 10.2 Phase 9 named-blocker pattern for EGMS-dependent CSLC cells

Phase 9 introduced the candidate-BINDING-with-named-blocker pattern for CSLC EU cells where EGMS L2a is required but unavailable. The pattern:
1. Run the CSLC eval to the point of requiring EGMS.
2. If EGMS download fails or stable-PS count falls below `min_valid_points`, write a structured named-blocker record with: the EGMStoolkit version, the EGMS token/credential state (short `?id=<token>` vs CLMS M2M API — currently no programmatic M2M path for EGMS as of 2026-04-15), the stable-PS count before and after filtering, and the error or fallback outcome.
3. Render the matrix cell as BINDING BLOCKER with the blocker name, not as CALIBRATING or BINDING FAIL.

The blocker name `required_aoi_binding_blocker` is reused across AOIs to keep matrix rendering consistent; the per-AOI evidence distinguishes them.

### 10.3 EGMStoolkit tooling state (as of v1.2)

EGMStoolkit 0.3.0 (Note: CLAUDE.md recommends 0.2.15; 0.3.0 was used for this eval run after manual patch to broken setup.cfg. Either version requires source install from GitHub.) (GitHub-only, broken `setup.cfg` requiring manual patch) is the current tooling. The EGMS download endpoint requires a short opaque `?id=<token>` copied from a portal-generated download link — there is no M2M programmatic path as of 2026-04-15 (investigated in `CONCLUSIONS_DISP_EU.md` §3.6). The CLMS M2M JWT flow (`@@oauth2-token` → Bearer → `@datarequest_post`) returns empty `downloadable_files` for all EGMS datasets. Any future phase resolving the Iberian blocker must either use a manually-obtained token or document a new programmatic path.

---

## 11. DISP ERA5/deramping/unwrapper diagnostics

<a name="disp-era5-deramping-unwrapper-diagnostics"></a>

**TL;DR:** Phase 10 established the ERA5 two-signal rule. Phase 11 ran SPURT native and PHASS post-deramping candidates against unchanged OPERA/EGMS references. PHASS post-deramping is retired due to SBAS inversion instability. SPURT's orbit-class ramp on Bologna (σ=7.1°) is the named blocker for v1.3.

> Cross-reference: §8 documents the Phase 10 ERA5 diagnostic run and the two-signal rule outcomes. This section documents the Phase 11 candidate evaluation methodology and the resulting Phase 12 posture evidence.

### 11.1 ERA5 two-signal rule (Phase 10)

ERA5 may only be promoted from diagnostic to required baseline when it shows at least two independent improvement signals simultaneously:
- Improved Pearson r (reference-agreement category)
- Lower absolute bias or RMSE (reference-agreement category)
- Reduced ramp magnitude without degrading product-quality evidence (ramp-attribution category)

Phase 10 outcomes: SoCal ERA5-on worsened reference agreement (r=0.0071 vs baseline 0.0490; bias=+55.43 vs +23.62 mm/yr). Bologna ERA5-on was effectively unchanged (r=0.3358 both runs; bias=+3.46 both runs). Neither cell met the two-signal rule. Phase 11 proceeded with the v1.1 global candidate order (SPURT first, then PHASS deramping) without ERA5 as a required baseline.

### 11.2 Phase 11 candidate evaluation methodology

Each candidate run:
1. Produces isolated output in `candidates/{candidate_name}/` directory (not overwriting baseline PHASS output).
2. Compares against the unchanged OPERA/EGMS reference using `prepare_for_reference(method=REFERENCE_MULTILOOK_METHOD)` — the same `block_mean` kernel as baseline.
3. Records a structured `DISPCandidateOutcome` sidecar with status (PASS/FAIL/BLOCKER), r, bias_mm_yr, rmse_mm_yr, mean_ramp_rad, ramp_sigma_deg, N_valid, and deformation_sanity_flagged.
4. Does not change native 5×10 m production output or `run_disp()` production defaults.

Candidate evidence surfaces in `metrics.json` as a `candidate_outcomes` list, in matrix compact hints as `cand=` entries in the product-quality column only (reference-agreement and ramp-attribution columns are unchanged), and in conclusions appendix sections.

### 11.3 PHASS deramping deformation sanity check

PHASS post-deramping (subtracting fitted planar ramps from per-IFG unwrapped phases before SBAS network inversion) is evaluated with a deformation sanity check that flags the candidate when:
- `abs(trend_delta_mm_yr) > 3.0` (velocity trend shifts by more than 3 mm/yr after deramping vs baseline)
- `abs(stable_residual_delta_mm_yr) > 2.0` (stable-terrain residual shifts by more than 2 mm/yr after deramping)

These thresholds are conservative relative to the known subsidence signal at Bologna (3–10 mm/yr). A flagged sanity check blocks a Phase 12 production recommendation for PHASS post-deramping — it does not prevent Phase 11 from recording candidate metrics.

Phase 11 outcomes: SoCal trend_delta=-390.89 mm/yr (flagged); Bologna trend_delta=-593.03 mm/yr (flagged). The cross-cell consistency and extreme magnitude indicate SBAS inversion instability caused by external IFG-level deramping, not a data artifact. See §12.2 for the PHASS retirement decision.

### 11.4 SPURT orbit-class attribution (Bologna)

SPURT native produces ramp attribution with `ramp_sigma_deg=7.1°` on Bologna — below the 30° orbit-class cutoff. This identifies a systematic orbital baseline contribution to the residual per-IFG ramps. By contrast, SoCal SPURT attribution is inconclusive (σ=84.8°). The orbit-class signal on Bologna is a diagnostic pointer: the residual 0.44 mm/yr bias gap (3.44 mm/yr measured vs 3.0 mm/yr criterion) has a testable intervention — tophu/SNAPHU with orbital baseline deramping applied before network inversion.

---

## 12. DISP deferred posture and v1.3 handoff

<a name="disp-deferred-posture"></a>

**TL;DR:** v1.2 closes with a DEFERRED posture for DISP production. Named blocker: SPURT orbit-class ramp on Bologna (σ=7.1°). Unblock: tophu/SNAPHU tiled unwrapping with orbital baseline deramping, both cells passing r > 0.92 AND bias < 3 mm/yr in the same run. SPURT native is the interim best candidate with explicit criteria-failure caveats. PHASS post-deramping is retired.

### 12.1 DEFERRED posture decision

Neither SPURT native nor PHASS post-deramping passed DISP reference-agreement criteria on either cell in Phase 11. Criteria: r > 0.92 AND bias < 3 mm/yr simultaneously.

| candidate | cell | r | bias_mm_yr | criteria met |
|-----------|------|---|------------|-------------|
| spurt_native | SoCal | 0.003 | +19.89 | Neither |
| spurt_native | Bologna | 0.325 | +3.44 | Neither |
| phass_post_deramp | SoCal | -0.116 | +21.96 | Neither (sanity-flagged) |
| phass_post_deramp | Bologna | 0.052 | -3.07 | Neither (sanity-flagged) |

No production recommendation can be made until the unblock conditions are met. The v1.2 production posture is DEFERRED.

### 12.2 PHASS post-deramping retirement

PHASS post-deramping is retired from the candidate ladder. The structural failure mode is SBAS re-inversion instability on externally deramped IFGs: the SBAS solver absorbs the subtracted ramp signal into unphysical long-wavelength deformation trends (trend_delta=-390.89 mm/yr SoCal, -593.03 mm/yr Bologna). The deformation sanity flag fired on both cells with consistent cross-cell magnitude. This is a method incompatibility — not a parameter-tuning issue and not specific to a single AOI. PHASS post-deramping should not appear as a v1.3 candidate step.

### 12.3 Named blocker and unblock condition

Named blocker: SPURT orbit-class ramp on Bologna (σ=7.1°), identifying a systematic orbital baseline contribution to the residual per-IFG ramps.

Unblock condition: Both SoCal and Bologna must pass r > 0.92 AND bias < 3 mm/yr in the same tophu/SNAPHU run with orbital baseline deramping enabled. Single-cell PASS is not sufficient.

Target milestone: v1.3.

### 12.4 Interim SPURT status

SPURT native is the best available candidate as of v1.2 but does not pass criteria on either cell. Bologna is the nearest (bias=3.44 mm/yr, 0.44 mm/yr from the 3.0 threshold; r=0.325, still far from 0.92). SoCal SPURT r=0.003/bias=+19.89 mm/yr is substantially further from criteria, driven by sparse connected-component coverage at the 5×10 m grid (N=40,050 vs 2.8M for PHASS). Use SPURT native only if production cannot wait for v1.3; document the criteria failures explicitly in any such deployment.

### 12.5 v1.3 recommended candidate order

1. **tophu/SNAPHU tiled unwrapping with orbital baseline deramping** — primary v1.3 candidate. The orbit-class attribution on Bologna (σ=7.1°) provides a testable hypothesis. Targets: both cells pass r > 0.92 AND bias < 3 mm/yr.
2. **20×20 m resolution fallback** — evaluate only if tophu/SNAPHU does not pass. This approach raises the architectural question of whether a 4× resolution-downgraded subsideo product remains OPERA-spec-compliant; the v1.3 milestone roadmapper should address this before committing.
3. **ERA5 + tophu/SNAPHU combined** — evaluate as a diagnostic option within v1.3 if tophu/SNAPHU alone does not pass the two-signal rule across both cells.

PHASS post-deramping is explicitly excluded from the v1.3 candidate order per §12.2.
