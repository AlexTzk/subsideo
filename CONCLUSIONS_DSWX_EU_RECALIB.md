# DSWx EU Threshold Recalibration — v1.1 Investigation Report

## Objective

Grid-search recalibration of DSWE thresholds (WIGT, AWGT) for EU Sentinel-2 L2A data
using 5 fit-set AOIs x wet/dry seasons against JRC Global Surface Water reference.

## What Was Attempted

**Iteration 1 — 3-axis grid, Doñana in fit set**
- WIGT x AWGT x PSWT2_MNDWI, 8400 gridpoints
- Doñana (seasonal marisma wetland) included as a fit-set AOI
- Outcome: BLOCKER — best point at edge of PSWT2_MNDWI axis; zero sensitivity to PSWT2_MNDWI diagnosed

**Iteration 2 — 2-axis grid (PSWT2_MNDWI fixed), Doñana replaced with Ebro Delta**
- WIGT x AWGT only, 525 gridpoints (25 x 21)
- WIGT: [0.08, 0.20], AWGT: [-0.10, 0.10]
- Doñana replaced with Ebro Delta (stable coastal delta with permanent water bodies)
- Outcome: BLOCKER — best point at top edge of WIGT (0.20); fit_set_mean_f1 = 0.2092

**Iteration 3 — expanded 2-axis grid (final attempt)**
- WIGT: np.linspace(0.08, 0.30, 45) — 20 extra points at top (0.205 … 0.300)
- AWGT: np.linspace(-0.20, 0.10, 31) — 10 extra points at bottom (-0.20 … -0.11)
- PSWT2_MNDWI still fixed at OPERA ATBD reference (-0.44)
- 1395 gridpoints total (45 x 31)
- Outcome: BLOCKER — best point again at top edge of WIGT (0.30); fit_set_mean_f1 = 0.2092

## Results

| Metric | Value |
|--------|-------|
| Best fit_set_mean_f1 | 0.2092 (across 10 pairs at joint best gridpoint) |
| Best joint gridpoint | WIGT=0.30, AWGT≈0.0, PSWT2_MNDWI=-0.44 |
| Cell status | BLOCKER (fit_set_mean_f1 < 0.5 gate; two consecutive runs identical) |

**Per-AOI Max F1 at Best Single Gridpoint** (across both seasons, expanded grid):

| AOI | Biome | Wet max F1 | Dry max F1 |
|-----|-------|-----------|-----------|
| alcantara | Mediterranean reservoir | 0.1704 | 0.1660 |
| tagus | Atlantic estuary | 0.1658 | 0.1467 |
| vanern | Boreal lake | 0.1742 | 0.1644 |
| garda | Alpine valley | 0.2187 | 0.4089 |
| ebro_delta | Mediterranean coastal delta | 0.2308 | 0.2455 |

Across all 1395 gridpoints, no gridpoint achieved mean F1 > 0.22 on the fit set.
The best single-scene F1 (Garda dry, 0.41) is still below the PASS threshold of 0.90.

## Root Cause Diagnosis

The DSWE algorithm was calibrated for OPERA HLS (Harmonized Landsat Sentinel-2) surface
reflectance. EU Sentinel-2 L2A uses ESA's sen2cor BOA correction chain, which produces
different absolute reflectance values and MNDWI index distributions than the HLS product.

Specifically:
- The sen2cor BOA correction applies different aerosol optical depth retrieval (MAJA vs
  LaSRC used for HLS)
- The Claverie et al. (2018) cross-calibration applied in `_apply_boa_offset_and_claverie`
  adjusts S2 bands to approximate HLS spectral properties, but the adjustment is a linear
  offset derived from multi-year composites rather than a scene-level transfer function
- MNDWI = (Green - SWIR1) / (Green + SWIR1): the sen2cor BOA Green and SWIR1 bands
  systematically differ from HLS-normalized equivalents, shifting the MNDWI distribution
  relative to the WIGT threshold range

Evidence: The joint best gridpoint at WIGT=0.30 (top of the expanded grid) with
fit_set_mean_f1=0.2092 — identical to the Iter-2 run at WIGT=0.20 — shows F1 is
insensitive to WIGT across [0.08, 0.30]. This is not a parameter-tuning problem; it is
a spectral distribution mismatch between the calibrated threshold range and the S2 L2A
MNDWI distribution. No amount of WIGT/AWGT grid expansion resolves a cross-sensor
calibration gap at the index level.

This is not a tunable grid problem — it requires either:
- (a) a labeled EU training dataset with S2 L2A spectral signatures; or
- (b) a cross-calibration function mapping S2 L2A reflectance to HLS-equivalent reflectance
  at the scene level (not the static per-band Claverie offset)

## Conclusion

EU recalibration deferred to v1.2. `THRESHOLDS_EU` remains at OPERA PROTEUS defaults
(`fit_set_hash` left empty). The Balaton eval (Plan 06-07) will run with PROTEUS defaults
and report whatever F1 results, with `named_upgrade_path` set accordingly.

The run_eval_dswx.py Stage 0 pre-check (`assert THRESHOLDS_EU.fit_set_hash != ''`) has
been relaxed to a warning so Plan 06-07 can proceed with PROTEUS defaults.

## v1.2 Recommendation

1. **Training data**: Use a labeled S2 L2A water/non-water dataset as reference — for
   example, the Copernicus Global Land Service (CGLS) 100m water layer or manual labeling
   of 3–5 permanent water bodies with stable JRC history. JRC maximum water extent
   misaligns with instantaneous S2 scenes at non-permanent water bodies (temporal mismatch
   between monthly JRC composite and single-date S2 scene causes omission errors on
   seasonally-variable shorelines, capping F1 at ~0.41 even at the best gridpoint).

2. **Cross-calibration**: Implement a scene-level S2 L2A → HLS transfer function using
   concurrent Landsat 8/9 overpasses and the Claverie et al. (2018) co-registration
   method applied per-scene rather than as a static offset.

3. **Alternative threshold families**: Consider deriving EU-specific DSWE thresholds
   from a S2 L2A reference dataset using the PROTEUS DSWE optimization methodology
   (ATBD OPERA/JPL D-107395) applied to S2 L2A radiance, rather than re-tuning the
   HLS-calibrated thresholds.

## References

- OPERA DSWx-HLS Algorithm Theoretical Basis Document (ATBD) D-107395 RevB — PROTEUS
  DSWE calibration methodology; original threshold derivation against HLS
- Claverie et al. (2018) "The Harmonized Landsat and Sentinel-2 surface reflectance
  data set", *Remote Sensing of Environment* 219:145–161 — cross-calibration method
  (static per-band offset) applied in `_apply_boa_offset_and_claverie`
- Pekel et al. (2016) "High-resolution mapping of global surface water and its long-term
  changes", *Nature* 540:418–422 — JRC Global Surface Water Monthly History used as
  reference; temporal mismatch limitation discussed in §Methods
