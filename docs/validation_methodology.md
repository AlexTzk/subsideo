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
| DISP ramp-attribution (reference-agreement diagnostic depth) | Phase 4 landed the multilook-method ADR in §3 (this doc); ramp-attribution per-cell evidence lives in CONCLUSIONS_DISP_N_AM.md §13 + CONCLUSIONS_DISP_EU.md §13 |
| DSWE F1 ≈ 0.92 architectural ceiling (product-quality interpretation) | Phase 5 or 6 will append (DSWX-07 named ML upgrade path is the authoritative evidence) |
| Cross-sensor precision-first framing (OPERA DIST vs EFFIS) | Phase 5 will append |
| OPERA frame selection by exact UTC hour (reference-agreement plumbing) | Phase 4 harness-first discipline will document |

(These sections are appended by later phases per CONTEXT D-15 append-only
policy. Phase 3 owns only §1 + §2 in this document; no stub headings for
later sections are pre-created.)

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
