# Phase 4: DISP-S1 Comparison Adapter + Honest FAIL - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 04-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 04-disp-s1-comparison-adapter-honest-fail
**Areas discussed:** Multilook method ADR, DISP self-consistency source, Ramp-attribution diagnostic, Brief + CONCLUSIONS shape

---

## Multilook method ADR

### Q1 — Which set of methods should `prepare_for_reference(..., method=...)` accept?

| Option | Description | Selected |
|--------|-------------|----------|
| All four | `Literal["gaussian", "block_mean", "bilinear", "nearest"]`. Captures PITFALLS-physics, FEATURES-conservative, current ad-hoc bilinear, and degenerate nearest. | ✓ |
| Two | gaussian + block_mean only. Loses continuity with v1.0 bilinear path. | |
| Three | + bilinear (no nearest). Drops nearest as user-hostile. | |

**User's choice:** All four (recommended)
**Notes:** Captures all four meaningful kernels for kernel-comparison studies in the follow-up milestone. Adapter validates at runtime; refuses None.

### Q2 — Which method does Phase 4 eval scripts pass explicitly?

| Option | Description | Selected |
|--------|-------------|----------|
| block_mean | Conservative, no kernel-flattery attack surface, matches OPERA's own multilook. | ✓ |
| gaussian | PITFALLS P3.1 physics argument; risk of "kernel inflated r" criticism. | |
| Both, side-by-side | Run both, report both columns. Doubles cost, adds matrix-cell ambiguity. | |

**User's choice:** block_mean (recommended)
**Notes:** Floor number we can defend; anyone arguing Gaussian gives higher r can rerun.

### Q3 — How does docs/validation_methodology.md §3 frame the multilook choice?

| Option | Description | Selected |
|--------|-------------|----------|
| ADR with PITFALLS+FEATURES dialogue | Sub-section presenting both arguments, naming the choice, citing criterion-immutability. | ✓ |
| Brief mention + cite | 1-2 paragraphs naming chosen method. Less defensible. | |
| Full ADR sub-document | Separate `docs/adr/004-multilook-method.md` file. ADR-tree rot risk. | |

**User's choice:** ADR with PITFALLS+FEATURES dialogue (recommended)
**Notes:** §3 ADR sub-section presents both arguments, names the choice, cites immutability principle; references PITFALLS P3.1 + FEATURES anti-feature table by name.

### Q4 — How is the chosen method enforced in the eval script + adapter?

| Option | Description | Selected |
|--------|-------------|----------|
| Constant + assertion | Module-level `REFERENCE_MULTILOOK_METHOD = "block_mean"`. Adapter raises ValueError if None. Phase 1 D-11 pattern. | ✓ |
| Interactive prompt | AskUserQuestion at script run. Breaks supervisor automation. | |
| Pydantic-settings env var | Configurable per-run; layer of indirection without git visibility. | |

**User's choice:** Constant + assertion (recommended)
**Notes:** Mirrors Phase 1 D-11 EXPECTED_WALL_S pattern; auditable in git diff.

---

## DISP self-consistency source

### Q1 — How is DISP self-consistency computed? (Coherence + residual stats)

| Option | Description | Selected |
|--------|-------------|----------|
| Mixed | Coherence from cached CSLC stack (Phase 3 helpers); residual from dolphin's velocity.tif. | ✓ |
| Pure-CSLC reuse | Both metrics from CSLC stack. Obscures unwrapper failure. | |
| Pure-DISP-output | Both metrics from dolphin output. Novel methodology; weakest semantic link. | |
| Pure-CSLC + diagnostic dolphin residual | Gate on CSLC; report dolphin-output residual as non-gate diagnostic. | |

**User's choice:** Mixed (recommended)
**Notes:** Captures BOTH input quality (coherence — should pass) and output quality (residual — will FAIL on PHASS-ramped output, which IS the intended honest-FAIL signal).

### Q2 — What stable_mask do we apply for the residual?

| Option | Description | Selected |
|--------|-------------|----------|
| Same as Phase 3 SoCal | build_stable_mask + 5km coast + 500m water + slope<10°. | ✓ |
| Mask cached from Phase 3 reused via search-path | RTC-EU pattern; saves ~1 min. | |
| Different parameters tuned for DISP | Loosen slope_max; goalpost-moving risk. | |

**User's choice:** Same as Phase 3 SoCal (recommended)
**Notes:** No per-AOI mask tuning per PITFALLS P2.1; numbers comparable across CSLC + DISP cells.

### Q3 — Which IFG stack feeds the coherence statistic for DISP cells?

| Option | Description | Selected |
|--------|-------------|----------|
| Same as Phase 3 | Sequential 12-day IFGs via boxcar 5×5; Phase 3 conventions. | ✓ |
| Dolphin's coherence layer | Couples validation to product. | |
| Both side-by-side | Sequential gate + dolphin-coh diagnostic. | |

**User's choice:** Same as Phase 3 (recommended)
**Notes:** SoCal: 14 IFGs from cached 15-epoch stack. Bologna: 18 IFGs from 19-epoch S1A+S1B stack. Direct cross-cell comparability.

### Q4 — For the SoCal cell: re-compute or reuse Phase 3's already-validated numbers?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse Phase 3 coherence, fresh DISP residual | Cross-cell read with provenance flag; saves ~12 min. | ✓ |
| Re-compute everything fresh | 12-min penalty per cold run. | |
| Reuse coherence + Phase 3 residual | Pure-CSLC reuse; conflicts with Q1=Mixed. | |

**User's choice:** Reuse Phase 3 coherence, fresh DISP residual (recommended)
**Notes:** SoCal coherence reads from `eval-cslc-selfconsist-nam/metrics.json`; provenance flag `coherence_source: 'phase3-cached'`. Bologna gets fresh everything (Phase 3 ran Iberian, not Bologna).

---

## Ramp-attribution diagnostic

### Q1 — Which diagnostics run as part of Phase 4 ramp-attribution?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) only, document (b)+(c) as deferred | Always-on per-IFG ramp fit. (b) POEORB swap + (c) ERA5 toggle deferred. Lowest dep surface. | ✓ |
| (a) + (b) | POEORB swap if RESORB epochs exist. No-op on current stacks. | |
| All three (a)+(b)+(c) | Adds pyaps3 + ~/.cdsapirc + 14-18 GB ERA5 download. Largest dep delta. | |
| (a) + opportunistic (b) when RESORB present | Auto-detect RESORB; reduces to (a)-only in practice. | |

**User's choice:** (a) only, document (b)+(c) as deferred (recommended)
**Notes:** SoCal Phase 3 window POEORB-only by D-Claude's-Discretion; Bologna 2021 fully POEORB-era. ERA5 not currently configured. Both (b)+(c) documented in CONCLUSIONS as available-but-deferred.

### Q2 — Where does the per-IFG ramp-fit code live?

| Option | Description | Selected |
|--------|-------------|----------|
| New helper in selfconsistency.py | `fit_planar_ramp(ifgrams_stack, mask)`. Pure-function, fits module charter. | ✓ |
| New helper in compare_disp.py | Closer to consumer; couples to DISP. | |
| Inline in run_eval_disp_*.py | Smallest surface; harder to test. | |
| scripts/diagnose_phass_ramps.py | Standalone CLI; cleanest separation; new script class. | |

**User's choice:** New helper in selfconsistency.py (recommended)
**Notes:** Module charter broadens to "Sequential-IFG self-consistency primitives" — coherent extension.

### Q3 — What schema does the ramp-attribution table follow in metrics.json + CONCLUSIONS?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-IFG list + aggregate | `ramp_attribution: {per_ifg: [...], aggregate: {...}, attributed_source: Literal[...]}`. | ✓ |
| Aggregate only | Just 4 aggregate numbers + label. Harder to audit per-IFG outliers. | |
| Full ramp model + per-pixel residual | Stores 2-D plane coefficients + ramp-removed residual rasters. v2 scope. | |

**User's choice:** Per-IFG list + aggregate (recommended)
**Notes:** Schema lives as new Pydantic v2 model in matrix_schema.py; additive, no breaking changes.

### Q4 — How does "PHASS FAIL" labelling get gated?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-attribute + human review | Rule produces label in metrics.json; human refines in CONCLUSIONS prose. | ✓ |
| Automated only | Rule output verbatim everywhere. Risk of misclassifying obvious cases. | |
| Always 'inconclusive' until brief author | Fully human attribution. Most conservative; slowest. | |

**User's choice:** Auto-attribute + human review (recommended)
**Notes:** Per Phase 2 D-15 investigation discipline ("automation flags, doesn't replace narrative"). Literal includes 'inconclusive' and 'mixed' so the rule never has to lie.

---

## Brief + CONCLUSIONS shape

### Q1 — How do CONCLUSIONS_DISP_N_AM.md / EU.md get updated?

| Option | Description | Selected |
|--------|-------------|----------|
| Append v1.1 sections + rename EGMS→EU | git mv CONCLUSIONS_DISP_EGMS.md → CONCLUSIONS_DISP_EU.md; preserve v1.0 narrative + append 4 v1.1 sections. | ✓ |
| Full v1.1 rewrite | Cleaner final document; loses audit trail. | |
| Create new CONCLUSIONS_DISP_SELFCONSIST_*.md alongside | Two CONCLUSIONS per cell; doubles surface; risk of divergence. | |

**User's choice:** Append v1.1 sections + rename EGMS→EU (recommended)
**Notes:** Preserves v1.0 planar-ramp discovery audit trail; matches manifest reference; matches Phase 3 D-08 "two CONCLUSIONS files per cell" pattern.

### Q2 — What numbers does DISP_UNWRAPPER_SELECTION_BRIEF.md cite as the FAIL state?

| Option | Description | Selected |
|--------|-------------|----------|
| Both: v1.1 reference-agreement + ramp-attribution numbers | Fresh r/bias from block_mean adapter + ramp aggregate. Drives candidate prioritisation. | ✓ |
| v1.1 reference-agreement only | Skips ramp-attribution detail. Loses diagnostic-driven prioritisation. | |
| v1.0 numbers only as historical reference | Defeats fresh-FAIL-numbers-fuel-the-brief logic. | |

**User's choice:** Both: v1.1 reference-agreement + ramp-attribution numbers (recommended)
**Notes:** Per-candidate success criterion can target either metric (r > X) or ramp aggregate (magnitude < Y rad).

### Q3 — What's the brief's per-candidate structure?

| Option | Description | Selected |
|--------|-------------|----------|
| 4 candidates × (description, success criterion, compute tier S/M/L, dep delta) | One-page markdown table-friendly. Research framing intentional. | ✓ |
| 5 candidates — add MintPy SBAS as 5th | Bloats without reason; doubles dep surface. | |
| Structured ADR with explicit decision frame | Heavier weight; risks brief growing into a plan. | |

**User's choice:** 4 candidates × (description, success criterion, compute tier S/M/L, dep delta) (recommended)
**Notes:** Candidates per FEATURES + ROADMAP: PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback. ~150-250 LOC single page.

### Q4 — Where exactly does the brief live + when does it get committed?

| Option | Description | Selected |
|--------|-------------|----------|
| .planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md | Co-located with Phase 2 + 3 probe artifacts. Committed at Phase 4 close. | ✓ |
| docs/disp-unwrapper-selection-brief.md | Wrong audience signal (research-handoff-internal, not product-facing). | |
| .planning/milestones/v1.2-disp-unwrapper-selection/SCOPING_BRIEF.md | Jumps the gun; v1.2 not yet roadmapped. | |

**User's choice:** `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md`, committed at Phase 4 close (recommended)
**Notes:** Co-located with `rtc_eu_burst_candidates.md` + `cslc_selfconsist_aoi_candidates.md`. Claude drafts; user reviews + greenlights before commit.

---

## Claude's Discretion

Areas where the user did not bind a specific value; plan-phase decides:

- `fit_planar_ramp` algorithm details (image vs UTM coordinates, masked vs full-burst, NaN policy)
- Auto-attribute rule cutoffs (direction-stability σ-cutoff, magnitude-vs-coherence Pearson cutoff)
- `EXPECTED_WALL_S` budget per cell (starting point: 6 hours per cell-script)
- `DISPCellMetrics` Pydantic v2 schema shape (additive extension of MetricsJson base)
- Bologna stable-mask data sources (Natural Earth default; revisit to OSM if buffer issues)
- Whether to render v1.0 ad-hoc-bilinear numbers in CONCLUSIONS as separate sub-section or footnote
- Brief publication date stamp framing
- Refactor scope (whether `compare_disp` Step 2 + `compare_disp_egms_l2a` internally call `prepare_for_reference` for consistency, or remain unchanged)

## Deferred Ideas

(Captured in 04-CONTEXT.md `<deferred>` section; summary)

- ERA5 tropospheric correction integration (DISP-V2-02; folded into Unwrapper Selection follow-up)
- POEORB swap automation when RESORB epochs are present
- Gaussian-kernel re-run for kernel-comparison study
- Promotion of `prepare_for_reference` to `validation/adapters.py`
- `fit_planar_ramp` returning per-IFG residual rasters
- DISP self-consistency on dolphin's coherence layer
- MintPy SBAS as 5th brief candidate
- Full ADR sub-document at `docs/adr/004-multilook-method.md`
- Brief stored in v1.2 milestone directory
- Per-cell `EXPECTED_WALL_S` budget tuning
- Bologna stable-mask via OSM coastlines
- v1.0 numbers continuity rendering style
