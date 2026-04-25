# DISP Unwrapper Selection Scoping Brief — v1.1-research handoff

**Drafted:** 2026-04-25 (Phase 4 close)
**Audience:** Future contributor picking up the DISP-V2-01 follow-up milestone
**Status:** Scoping brief; **NOT** a plan. Candidates proposed; success criteria proposed. The follow-up milestone commits.

> Per CONTEXT D-15 / D-16: 4-candidate framing intentional (NO MintPy SBAS as 5th candidate). Brief lives in `.planning/milestones/v1.1-research/` (the canonical home for forward-looking research artifacts). Author = Claude (research output); user reviews + greenlights before commit per CONTEXT D-16.

## Context

Phase 4 of v1.1 ran the existing dolphin/PHASS pipeline against:

- **N.Am. SoCal** `t144_308029_iw1` — 15 epochs Jan-Jun 2024, 14 sequential 12-day IFGs (POEORB-only era)
- **EU Bologna** `t117_249422_iw2` — 19 epochs Jan-Jun 2021, 9 sequential 12-day pairs (S1A+S1B cross-constellation 6-day cadence; only 9 pairs fall on the 11–13-day window per the `_is_sequential_12day(...) <= 1 day` filter; fully POEORB-era)

Both runs use cached CSLCs from `eval-disp/cslc/` and `eval-disp-egms/cslc/`; no SAFE re-downloads. Phase 4 changes are validation-side only (adapter, ramp-fit, separated metrics) — the dolphin/PHASS/MintPy pipeline algorithm is unchanged per CONTEXT D-20.

### Reference-agreement (block_mean adapter, fresh)

| Cell | r | bias_mm_yr | RMSE_mm_yr | n | Verdict |
|------|---|------------|------------|---|---------|
| N.Am. SoCal vs OPERA DISP-S1 30m | 0.0490 | +23.6153 | 59.5567 | 481,392 | FAIL (r > 0.92, bias < 3 mm/yr) |
| EU Bologna vs EGMS L2a PS | 0.3358 | +3.4608 | 5.2425 | 1,126,687 | FAIL |

(Continuity note: v1.0 numbers using `Resampling.bilinear` were r=0.0365 / bias=+23.62 mm/yr (N.Am.) and r=0.3198 / bias=+3.3499 mm/yr (EU). The block_mean numbers above are the conservative-kernel official metric per CONTEXT D-02 + `docs/validation_methodology.md` §3. Kernel choice does NOT inflate the metric — both v1.0 and v1.1 numbers fail r > 0.92 by an order of magnitude.)

### Product-quality (CALIBRATING, separately reported per CONTEXT D-08 + D-19)

| Cell | coh_med_of_persistent | coh_source | residual_mm_yr | cell_status |
|------|----------------------|------------|----------------|-------------|
| N.Am. SoCal | 0.8868 | phase3-cached | -0.0303 | MIXED |
| EU Bologna | 0.0000 | fresh | +0.1170 | MIXED |

Coherence is computed at native 5×10 m on stable terrain (Phase 3 D-09 mask: WorldCover class 60 + slope < 10° + coast buffer 5 km + water buffer 500 m). Residual is computed fresh from dolphin's `velocity.tif` per CONTEXT D-08 (the residual is what we're validating; never cross-cell-read).

The Bologna `coh_med_of_persistent = 0.000` is a real signal — no pixel exceeded the 0.6 coherence threshold in EVERY one of the 9 IFGs over the Po-plain agricultural mask (mean 0.219, p75 0.316, both below 0.6). Po plain has fundamentally lower stable-terrain coherence than SoCal Mediterranean / chaparral.

### Ramp attribution (CONTEXT D-09..D-12)

| Cell | mean_magnitude_rad | direction_sigma_deg | r(magnitude, coherence) | n_ifgs | attributed_source |
|------|-------------------|--------------------|-------------------------|--------|-------------------|
| N.Am. SoCal | 35.5881 | 124.5336 | +0.1520 | 14 | `inconclusive` |
| EU Bologna | 25.9980 | 117.0968 | -0.5173 | 9 | `inconclusive` |

Per CONTEXT D-09, only diagnostic (a) per-IFG planar-ramp fit ran. Diagnostic (b) POEORB swap is no-op-on-current-stacks (both cells fully POEORB-era). Diagnostic (c) ERA5 toggle requires `pyaps3 >= 0.3.6` + valid `~/.cdsapirc` (DISP-V2-02 in REQUIREMENTS, deferred per CONTEXT D-09 + folded into Unwrapper Selection follow-up as secondary).

The `inconclusive` label on both cells is informative on its own: per-IFG ramp magnitudes are large (mean 26–36 rad, well above v1.0's 1.0-rad soft-flag threshold) but ramp directions cluster randomly (sigma > 100° on both cells, far above the 30° orbit-class cutoff) and coherence-correlation is weak/negative (+0.15 / -0.52, both far from the 0.5 phass-class cutoff). The cross-cell pattern — large random-direction ramps with coherence-uncorrelated-to-negative magnitudes — does not fit any single-source attribution. Atmospheric long-wavelength curvature is a candidate that diagnostic (c) would clarify.

## Candidate approaches

| # | Approach | Description | Success criterion | Compute tier | Dep delta |
|---|----------|-------------|-------------------|--------------|-----------|
| 1 | **PHASS + post-deramping** | Keep PHASS unwrapper; subtract per-IFG planar-ramp fit BEFORE dolphin's network inversion. Re-runs from cached unwrapped IFGs. | r > 0.5 OR mean ramp magnitude < 1.0 rad on the post-deramped stack (current SoCal mean 35.6 rad / EU 26.0 rad) | **S** — post-process only (~5 min/cell, M3 Max) | numpy lstsq (already in dolphin); no new conda packages |
| 2 | **SPURT native** | Switch dolphin's `unwrap_method` from PHASS to SPURT (graph-based unwrapper for large grids, designed for OPERA DISP). One-line config. | r > 0.7 (intermediate target) AND `auto_attribute_ramp` returns `'inconclusive'` after re-run with mean ramp magnitude < 5 rad | **M** — re-unwrap from cached IFGs (~30 min/cell) | None (SPURT shipped with dolphin 0.42.5 via conda-forge) |
| 3 | **tophu + SNAPHU multi-scale tiled** | Use tophu's tile-based decomposition (3×3 tiles, 30 m downsample factor) wrapping SNAPHU. Empirically validated for OPERA DISP large-scale. | r > 0.85 AND PASS reference-agreement gate on at least one of (N.Am., EU) | **L** — re-unwrap from cached IFGs at multi-scale (~60 min/cell) | tophu 0.2.1 + snaphu 0.4.1 conda-forge (already in conda-env.yml; v1.0 had hand-pip-install issue resolved in Phase 1 ENV-02) |
| 4 | **20×20 m fallback multilook** | Multilook CSLC stack to 20×20 m BEFORE phase linking. Reduces per-IFG pixel count by ~6× (5×10 m → 20×20 m), makes any unwrapper tractable. | PASS reference-agreement gate at 30 m comparison after multilook (PASS = the v1.0 PROJECT.md bar of r > 0.92, bias < 3 mm/yr) | **L** — re-run dolphin from CSLC stack with downsample option (~3 h/cell cold) | None (dolphin native multilook config); only adds compute |

## Per-candidate notes

### 1. PHASS + post-deramping

The cheapest of the 4 — runs entirely on already-cached unwrapped IFGs. If the ramp signature were `phass`-class (cell-by-cell PHASS-class attribution), removing the ramp BEFORE network inversion would bring r above the FAIL threshold without re-unwrapping. Phase 4's `inconclusive` label on both cells weakens this candidate's a-priori success probability — the ramps are not phass-class.

**Risk:** if the ramp signal contains real long-wavelength deformation (e.g., interseismic strain accumulation), deramping discards signal alongside artefact. SoCal is a tectonic AOI; this needs a sanity check against Nevada Geodetic Lab GPS residuals (CSLC-V2-01 future work). Bologna's negative coh-magnitude correlation (-0.52) suggests atmospheric curvature, which deramping would correctly remove.

### 2. SPURT native

If the PHASS-class label drives a real-vs-artefact decision per (1), SPURT becomes the production fix. dolphin 0.42.5's `unwrap_method='spurt'` is a one-line config switch in `run_disp.py`'s dolphin invocation. SPURT's graph-based unwrapping is the OPERA-recommended approach for large grids (PITFALLS / FEATURES alignment). Phase 4's `inconclusive` label argues for SPURT specifically — if PHASS isn't producing recognisable phass-class ramps, switching to a different unwrapper class is more useful than tuning PHASS post-process.

**Risk:** SPURT may not converge on all 14-9 IFGs in current cell stacks; failures need a fall-back path (PHASS or candidate 3). Bologna's low coherence (mean 0.22) is a concern — SPURT's graph-cut tolerance on near-zero-coherence cells is not empirically validated for v1.1 stacks.

### 3. tophu + SNAPHU multi-scale tiled

The compute-heaviest of the network-inversion candidates. tophu's tiling (3×3 spatial tiles + 30 m downsample) is what OPERA DISP uses internally; a faithful subsideo replication should match. v1.0 had a SNAPHU pip-install issue (`CONCLUSIONS_DISP_N_AM.md` §5.2 hung at integration); Phase 1 ENV-02 conda-forge resolution removes the historical blocker.

**Risk:** tophu is the heaviest compute path (~60 min/cell). Worth running only if (1) and (2) both FAIL.

### 4. 20×20 m fallback multilook

The cleanest "give up on native resolution but get an honest PASS" path. Multilooking CSLC stack to 20×20 m before phase linking reduces aliasing risk and makes any unwrapper tractable.

**Risk:** Pre-commits subsideo to a 4× resolution downgrade. Acceptable for a v1.2 release if (1)/(2)/(3) all FAIL their criteria, but should be the last fallback per CONTEXT 04-CONTEXT.md §Specifics ("the FAIL is the intended signal" — not a permission to give up on native). This candidate also raises the architectural question: does a 20×20 m subsideo product remain `subsideo`, or does it become a different product class? The follow-up milestone roadmapper should answer this before committing to (4).

## Attribution-driven prioritisation (per CONTEXT D-14)

Phase 4 ramp_attribution labels:
- N.Am. SoCal: `inconclusive`
- EU Bologna: `inconclusive`

Decision tree (Phase 4 v1.1 closure):
- If both 'phass' → all 4 candidates remain viable; **prioritise (1) for fastest signal, (2) for production fix.**
- If 'orbit' → candidates (1)+(2) become lower-priority (don't address orbit-state-vector errors); diagnostic (b) POEORB swap re-prioritises if the future window has RESORB epochs.
- If 'tropospheric' → all candidates lower-priority; diagnostic (c) ERA5 toggle re-prioritises (DISP-V2-02).
- If 'mixed' or 'inconclusive' → diagnostic (b) + (c) BEFORE candidate evaluation.

**Phase 4 result: BOTH cells produce `inconclusive`.** Per the decision tree, the brief author's recommendation for the v1.2 roadmapper is:

1. **First step (zero compute):** activate diagnostic (c) ERA5 toggle by integrating `pyaps3 >= 0.3.6` (DISP-V2-02). The cross-cell pattern (large random-direction ramps; SoCal r(mag,coh)=+0.15 / EU r(mag,coh)=-0.52) suggests atmospheric long-wavelength curvature. ERA5 correction subtracts this directly; if r jumps after ERA5 the label becomes 'tropospheric' and candidate (1) PHASS+deramping becomes the fastest production fix.
2. **If ERA5 doesn't recover r:** start with **(2) SPURT native** (the cheapest unwrapper-class switch that addresses the structural unwrapper limitation). SoCal r=0.049 is so far from the bar that the most likely path to PASS is a different unwrapper, not a different post-process.
3. **If (2) FAILs:** **(1) PHASS+post-deramping** as a residual-artefact mop-up. If (1) brings either cell to r > 0.5, that's a useful intermediate signal even if FAIL.
4. **If (1)+(2) both FAIL:** escalate to **(3) tophu+SNAPHU multi-scale**. Compute cost is justified once cheaper candidates exhausted.
5. **(4) 20×20 m fallback** ONLY if (1)+(2)+(3) all FAIL. Pre-commits a resolution downgrade; should be the last resort per CONTEXT.

## Out of scope for this brief

- **MintPy SBAS as 5th candidate** — intentional 4-candidate framing per CONTEXT D-15. Could be added in the follow-up milestone if (1)+(2)+(3)+(4) all FAIL their per-candidate success criteria.
- **ERA5 tropospheric correction integration** — DISP-V2-02 in REQUIREMENTS; folded into the follow-up milestone as secondary (per CONCLUSIONS_DISP_EU §13.4 / §6 candidate-mitigations). The brief recommends activating diagnostic (c) FIRST in the follow-up milestone given Phase 4's inconclusive cross-cell pattern.
- **Production unwrapper choice** — this brief proposes; the follow-up milestone commits.
- **Specific candidate threshold values** — the success criteria above are first-pass targets derived from the FAIL numbers in the §Context tables. The follow-up milestone tunes these against measured candidate r/bias.

## Open questions (for the v1.2 milestone roadmapper)

1. **Diagnostic (c) ERA5 toggle:** does the v1.2 milestone include integration of `pyaps3 >= 0.3.6` ERA5 download path (CDS API key required), or does it stay deferred? CONTEXT D-09 says "available; deferred"; the follow-up milestone should absorb DISP-V2-02 here given Phase 4's `inconclusive` × 2 outcome strongly suggests atmospheric contribution.
2. **Candidate ordering after attribution:** Phase 4's both-cells-`inconclusive` outcome triggers the "diagnostics (b)+(c) BEFORE candidate evaluation" branch. If ERA5 (diagnostic c) flips both cells to 'phass', the brief recommends (1) → (2) → (3) → (4). If ERA5 only flips one cell to 'phass' and the other to 'tropospheric' or 'mixed', do we order differently per cell?
3. **Held-out test cell:** v1.2 should validate on a cell NOT in v1.1 (neither SoCal nor Bologna) to avoid overfitting candidate selection. Candidate AOIs: a SoCal winter window (forces RESORB epochs → unlocks diagnostic b), or an N. African desert burst (low coherence; tests SPURT robustness).
4. **Production resolution decision:** if (4) 20×20 m fallback achieves PASS, is the production default downgraded to 20×20 m, or kept at native 5×10 m with the multilook as a validation-only fallback (mirroring `prepare_for_reference` validation-only discipline)? CONTEXT 04-CONTEXT.md §Specifics + DISP-05 say "Native 5×10 m stays production default" categorically; the v1.2 milestone may override only with explicit roadmap decision.
5. **Bologna coherence floor:** Bologna's `persistently_coherent_fraction = 0.000` is the cell-specific finding that may need a different `gate_metric_key` (CONTEXT D-04 escape valve) at v1.2 promotion-to-BINDING. The follow-up milestone should examine whether the gate stat itself needs to flex for low-coherence agricultural cells.

## Sources

- v1.0 CONCLUSIONS: `CONCLUSIONS_DISP_N_AM.md` §5.1 (PHASS planar-ramp discovery), `CONCLUSIONS_DISP_EU.md` §4.3 (38 of 38 IFGs flagged in v1.0 EU eval; was named `CONCLUSIONS_DISP_EGMS.md` until Phase 4 D-13 rename).
- Phase 4 metrics.json: `eval-disp/metrics.json` (SoCal — 14 PerIFGRamp records), `eval-disp-egms/metrics.json` (Bologna — 9 PerIFGRamp records).
- Phase 4 methodology: `docs/validation_methodology.md` §3 (multilook ADR — Phase 4 D-03).
- Research: `.planning/research/PITFALLS.md` §P3.1 / §P3.2; `.planning/research/FEATURES.md` lines 67-76 / 142-143.
- v1.1 REQUIREMENTS: DISP-V2-01 (this brief is the v1.1 deliverable that scopes the V2 milestone), DISP-V2-02 (ERA5 tropospheric correction, secondary in follow-up).

---

**As of 2026-04-25, this brief is the v1.1 closure handoff. The follow-up milestone roadmapper consumes it as input when v1.2 (or whichever version) starts.**
