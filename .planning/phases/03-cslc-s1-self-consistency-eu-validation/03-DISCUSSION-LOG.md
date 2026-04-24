# Phase 3: CSLC-S1 Self-Consistency + EU Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 03-cslc-s1-self-consistency-eu-validation
**Areas discussed:** Coherence gate metric + calibration framing, Script + matrix cell layout, Stack sourcing + AOI probe strategy, docs/validation_methodology.md scope (CSLC-06)

---

## Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Coherence gate metric + calibration framing | P2.2 research flag (MEDIUM uncertainty): which of the 5 stats plugs into coherence_min=0.7. Plus M5 CALIBRATING first-rollout reporting. Blocks SoCal calibration run. | ✓ |
| Script + matrix cell layout | 3 per-AOI scripts vs 2 declarative scripts (5×2 symmetry). Determines CONCLUSIONS file count + matrix row count. | ✓ |
| Stack sourcing + AOI probe strategy | Where SoCal's 15 epochs come from; Mojave + Iberian probe artifact; fallback exhaustion blocker trigger. | ✓ |
| docs/validation_methodology.md scope (CSLC-06) | CSLC cross-version only, bootstrap full file with stubs, or CSLC + product-quality/reference-agreement sections. | ✓ |

**User's choice:** All four areas discussed.

---

## Coherence gate metric + calibration framing

### Q1: Which coherence statistic is the BINDING input to the coherence_min=0.7 gate?

| Option | Description | Selected |
|--------|-------------|----------|
| Median of persistently-coherent pixels | P2.2 proposed mitigation. Decouples gate from mask-definition problems; robust to bimodal contamination (dunes/playa). Ships all 5 stats; gate reads this one. | ✓ |
| Median over stable mask | Per-pixel mean across 14-IFG stack then median over stable mask. Simpler: no persistently-coherent masking. | |
| Persistently-coherent fraction | Fraction of stable-mask pixels > 0.6 in all 14 IFGs. Requires retargeting the 0.7 threshold. | |
| Mean over stable mask | Current `selfconsistency.py` default. Research P2.2 warns mean is pulled down by 0.3-coherence tail even on working chains. | |

**User's choice:** Median of persistently-coherent pixels
**Notes:** `selfconsistency.coherence_stats()` extends additively with `median_of_persistent` 6th key; no signature change. `gate_metric_key` field added to CRITERIA['cslc.selfconsistency.coherence_min'] for auditability.

### Q2: What per-IFG coherence threshold defines 'persistently coherent'?

| Option | Description | Selected |
|--------|-------------|----------|
| 0.6 (selfconsistency.py default) | `DEFAULT_COHERENCE_THRESHOLD = 0.6`. Literature: individual 12-day S1 IFG coherence on stable bedrock is 0.7–0.85; 0.6 admits real stable pixels. | ✓ |
| 0.5 | More permissive. Safer floor for Mojave fallback AOIs. Risk: admits marginally-coherent pixels. | |
| 0.7 | Tighter; matches gate-value 0.7. Risk: drops Mediterranean-vegetation contaminated pixels. | |
| Claude's Discretion — SoCal sweep at plan-phase | Defer; run 0.5/0.6/0.7 sweep during SoCal execution. Extra sub-task. | |

**User's choice:** 0.6 (selfconsistency.py default)
**Notes:** Reuse ship default; no plan-phase sweep. Fixed across all 3 AOIs for cross-AOI comparability.

### Q3: How is SoCal's first-rollout CALIBRATING result reported (M5)?

| Option | Description | Selected |
|--------|-------------|----------|
| Matrix cell = "CALIBRATING: coh=0.XX / resid=Y.Y" | Strict Phase 1 D-03 rendering: italicised cell, raw value, no PASS/FAIL until ≥3 data points (GATE-05 + M5). CONCLUSIONS labels "calibration data point" not "PASS." | ✓ |
| PASS/FAIL with CALIBRATING annotation | Cell reads PASS/FAIL against 0.7 but annotated with ⚠ CALIBRATING badge. Risk: M1 target-creep. | |
| Defer to plan-phase | Claude picks rendering during plan-phase based on matrix_writer extension. | |

**User's choice:** Matrix cell = "CALIBRATING: coh=0.XX / resid=Y.Y"
**Notes:** `all_pass` in aggregate becomes null for CALIBRATING cells; new `cell_status: Literal['PASS', 'FAIL', 'CALIBRATING', 'MIXED', 'BLOCKER']` enum introduced in Phase 3.

### Q4: If SoCal's gate stat lands clearly below 0.7 through definitional/contamination reason, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Methodology change, not threshold change | P2.2 research mitigation: switch the gate STAT (e.g., to persistently-coherent-fraction), threshold 0.7 stays. Add `gate_metric_key` to criteria registry for auditability. | ✓ |
| Mask-tightening before stat change | Try exclude_mask per-AOI first; only if gate still < 0.7, switch stat. Keeps stat invariant. | |
| Both — sequenced (mask first, then stat) | Try mask tightening → report diagnostics → change stat as last resort. Most defensive, most work. | |

**User's choice:** Methodology change, not threshold change
**Notes:** Documentation lives in CONCLUSIONS "Calibration Changes" subsection; `gate_metric_key` change is auditable in matrix-writer output per Phase 1 D-03 drift-visibility mechanism.

### Q5: Move to next area, or more questions?

| Option | Description | Selected |
|--------|-------------|----------|
| Next area | Coherence gate captured: gate stat = median of persistently-coherent, threshold=0.6, first-rollout=CALIBRATING, escape valve=methodology change. | ✓ |
| More questions | Dig deeper: US stable-pixel def, residual-velocity anchor, IFG boxcar size, gate_metric_key surfacing. | |

**User's choice:** Next area

---

## Script + matrix cell layout

### Q1: How are the 3 AOIs organized into eval scripts?

| Option | Description | Selected |
|--------|-------------|----------|
| 2 scripts: run_eval_cslc_selfconsist_nam.py + run_eval_cslc_selfconsist_eu.py | N.Am. script has `AOIS = [SoCal, Mojave]`; EU script has `AOIS = [Iberian]`. Mirrors Phase 2 pattern (declarative list + per-AOI try/except). Matches 5×2 matrix symmetry. | ✓ |
| 3 separate scripts (FEATURES suggestion) | `run_eval_cslc_selfconsistency.py`, `_mojave.py`, `run_eval_cslc_eu.py`. Triples CONCLUSIONS count, breaks 5×2. | |
| 1 script with full AOI list | `AOIS = [SoCal, Mojave, Iberian]` with region field. Bundles NAm+EU credentials/caches. | |

**User's choice:** 2 scripts (nam + eu) with declarative AOI lists
**Notes:** Per-AOI try/except isolation per Phase 2 D-06; supervisor wraps each script; `_mp.configure_multiprocessing()` fires once at `run_cslc()` top.

### Q2: How do the 2 scripts render into matrix cells?

| Option | Description | Selected |
|--------|-------------|----------|
| 2 aggregate cells (cslc:nam, cslc:eu) with per-AOI nested | Phase 2 pattern. `cslc:nam` = 2-AOI aggregate (SoCal+Mojave) with `per_aoi` nested. `cslc:eu` = 1-AOI. Matrix row = `X/N CALIBRATING`. | ✓ |
| 3 matrix rows (one per AOI) | `cslc:nam-socal`, `cslc:nam-mojave`, `cslc:eu-iberian` as 3 separate manifest entries. Breaks 5×2. | |

**User's choice:** 2 aggregate cells with per-AOI nested
**Notes:** Preserves Phase 1 10-cell matrix shape; writer adds italicised CALIBRATING rendering per Phase 1 D-03.

### Q3: Does SoCal also run OPERA CSLC amplitude sanity, or only self-consistency?

| Option | Description | Selected |
|--------|-------------|----------|
| SoCal: both; Mojave: self-consistency only; Iberian: both | v1.0 SoCal already has r=0.79/RMSE=3.77 dB → continuity. Mojave skips amp sanity — saves up to 4 OPERA CSLC downloads in fallback chain. Iberian: CSLC-05 explicit. | ✓ |
| All three run amplitude sanity | Extra OPERA CSLC download for Mojave. | |
| Only Iberian (EU matrix cell requires it) | Strict; loses SoCal continuity with v1.0 number. | |

**User's choice:** SoCal + Iberian amplitude sanity; Mojave self-consistency only
**Notes:** `reference_agreement` field is null for Mojave per-AOI record; SoCal first-epoch OPERA CSLC is the amp-sanity reference.

### Q4: How are CONCLUSIONS docs organized?

| Option | Description | Selected |
|--------|-------------|----------|
| 2 files: CONCLUSIONS_CSLC_SELFCONSIST_NAM.md + CONCLUSIONS_CSLC_EU.md | One per script/cell. N.Am. covers SoCal+Mojave side-by-side. Mirrors Phase 2's single CONCLUSIONS_RTC_EU.md for 5 bursts. | ✓ |
| 3 files (FEATURES list) | One per AOI. Triples artifact count. | |
| 1 file: CONCLUSIONS_CSLC_SELFCONSIST.md | All three AOIs in one doc. Mixes N.Am. + EU regions. | |

**User's choice:** 2 CONCLUSIONS files (nam + eu)
**Notes:** New required sections per CONCLUSIONS: Calibration Framing (M5 discipline), Stable-Mask Sanity Check (P2.1 mitigation artifacts), Calibration Changes (gate_metric_key change log).

### Q5: Move to next area, or more questions?

| Option | Description | Selected |
|--------|-------------|----------|
| Next area | Script/matrix captured: 2 scripts, 2 cells, SoCal+Iberian amp sanity, 2 CONCLUSIONS. | ✓ |
| More questions | Dig deeper: BurstConfig shape, supervisor EXPECTED_WALL_S, meta.json nested hashes, matrix manifest entries. | |

**User's choice:** Next area

---

## Stack sourcing + AOI probe strategy

### Q1: Where do SoCal's 15 epochs (14 sequential 12-day IFGs) come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Fresh 15-date download, eval-cslc-selfconsist-nam/input/ | New cache dir, 15 consecutive S1A IW SLC scenes over burst t144_308029_iw1 across 168-day window. ~117 GB download, 2-3 h on residential bandwidth. Clean ownership, no cross-cell cache entanglement. | ✓ |
| Reuse Phase 1 DISP-N.Am. CSLC stack | Zero download cost. Con: epoch count may be N≠15; schedule coupling. | |
| harness.find_cached_safe fallback across eval dirs | Phase 2 D-02 pattern. Most compute-frugal; hardest cache invalidation. | |

**User's choice:** Fresh 15-date download under eval-cslc-selfconsist-nam/input/
**Notes:** SoCal is the calibration anchor for a new gate; isolation > compute frugality. Exact sensing window is Claude's Discretion at plan-phase (prefer clean POEORB coverage, avoid Nov 2023 S1B EOL transition).

### Q2: Does Phase 3 get a dedicated probe artifact for Mojave + Iberian?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — one combined probe doc | `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md`. Claude drafts burst IDs + coverage data; user reviews in plan-phase. Phase 2 D-01 discipline. | ✓ |
| Yes — two probe docs (NAm + EU) | Separation at cost of 2 artifacts. | |
| No — Claude picks bursts inline in plan-phase | Skip probe; Claude proposes directly in PLAN.md. Saves a file, loses audit trail. | |

**User's choice:** One combined probe doc covering Mojave + Iberian
**Notes:** Columns: aoi, regime, candidate_burst_id, opera_cslc_coverage_2024, egms_l2a_stable_ps_count (EU only), expected_stable_pct_per_worldcover, published_insar_stability_ref, cached_safe_fallback_path. Committed before eval runs.

### Q3: CSLC-04 fallback exhaustion: when does Mojave surface a blocker?

| Option | Description | Selected |
|--------|-------------|----------|
| Probe all 4 upfront; try in probe-locked order; blocker if all 4 fail | Probe pre-ranks Coso/Searles, Pahranagat, Amargosa, Hualapai. Eval tries in order; each attempt writes AOIResult. All 4 fail → supervisor exits 1, matrix cell shows `1/2 CALIBRATING, 1/2 BLOCKER`. | ✓ |
| Primary only; any FAIL is a blocker | Strict. Fallback list exists to cover CSLC reference absence, not gate failures. | |
| Claude's Discretion — lock in plan-phase based on probe | Defer. | |

**User's choice:** Probe all 4, try in order, blocker if all fail
**Notes:** New `AOIResult.attempts: list[AttemptResult]` sub-list for Mojave chain; first CALIBRATING/PASS result wins; supervisor exits 1 only if all fail. CSLC-04 met via surfaced BLOCKER status in metrics.json, not silent FAIL.

### Q4: Iberian EGMS L2a stable-PS definition + acquisition?

| Option | Description | Selected |
|--------|-------------|----------|
| mean_velocity_std < 2 mm/yr via EGMStoolkit + compare_disp._load_egms_l2a_points | BOOTSTRAP §2 threshold. Reuse existing loader via cross-module import. New helper compare_cslc_egms_l2a_residual(). Residual = mean(|our - egms|) in mm/yr after reference-frame alignment. | ✓ |
| Use Ortho (raster) instead of L2a (point) | Simpler grid math; loses PS selection filter. Research names L2a explicitly. | |
| Defer to plan-phase | Plan-phase decides threshold + loader. | |

**User's choice:** mean_velocity_std < 2 mm/yr via EGMStoolkit + _load_egms_l2a_points reuse
**Notes:** compare_cslc_egms_l2a_residual() lives in compare_cslc.py; imports _load_egms_l2a_points from compare_disp.py; uses selfconsistency.residual_mean_velocity frame anchor logic.

### Q5: Move to next area, or more questions?

| Option | Description | Selected |
|--------|-------------|----------|
| Next area | Stack/probe captured: SoCal fresh 15-date download; 1 combined probe doc; Mojave probe-ordered 4-candidate try-chain with BLOCKER escape; Iberian EGMS L2a stable-PS threshold 2 mm/yr. | ✓ |
| More questions | Dig deeper: SoCal sensing window choice, OPERA CSLC batch-fetch, residual chain MintPy-vs-linear-fit, US stable-pixel definition. | |

**User's choice:** Next area

---

## docs/validation_methodology.md scope (CSLC-06)

### Q1: What does Phase 3 write into docs/validation_methodology.md?

| Option | Description | Selected |
|--------|-------------|----------|
| CSLC cross-version section + product-quality vs reference-agreement distinction section | Phase 3 owns 2 sections it has authoritative evidence for. Phase 7 REL-03 adds §3 OPERA frame selection + §4 DSWE ceiling + §5 cross-sensor framing. | ✓ |
| CSLC cross-version section only | Strict CSLC-06 reading. Phase 7 consolidates all 4 findings + the distinction. | |
| Full doc with stubs for other 3 findings | Phase 3 bootstraps the whole file with stub headings. Stub-rot risk. | |

**User's choice:** CSLC + product-quality vs reference-agreement sections
**Notes:** Iberian row (three independent numbers) is the motivating example for §2; each phase writes what it has evidence for; no stub scaffolding.

### Q2: Cross-version phase section evidence grade?

| Option | Description | Selected |
|--------|-------------|----------|
| Consolidate CONCLUSIONS §5 + structural isce3 interpolation-kernel argument | Structural argument first (closes the door); diagnostic evidence (carrier/flatten/both → coh 0.002) second. Cites isce3 0.15→0.19 changelog + P2.4. | ✓ |
| Diagnostic evidence only | Walk CONCLUSIONS §5 experiments in more detail; skip structural argument. Reader can imagine "one more correction". | |
| Optional: add P2.4 isce3 minor-version diagnostic | Research LOW confidence; ~2 days work; not a milestone gate. Strengthens the argument. | |

**User's choice:** Consolidate CONCLUSIONS §5 + structural isce3 interpolation-kernel argument
**Notes:** §1 opens with structural argument (interpolation kernel changed between isce3 0.15 and 0.25) to close the P2.4 anti-pattern permanently. Contains "do not re-attempt" policy statement for future contributors.

### Q3: How is docs/validation_methodology.md maintained post-Phase-3 (pre-Phase 7)?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 4/5/6 each APPEND their sections (no stub scaffolding) | Each phase appends its contribution. Phase 3 = §1+§2. Phase 4 = §3 DISP. Phases 5/6 = §4+§5. Phase 7 writes TOC + final consistency pass. | ✓ |
| Phase 3 writes full TOC + stubs; later phases fill | Reader sees shape early; stub deviation risk. | |
| Phase 3 writes 2 sections standalone; Phase 7 copies + restructures | Double-write; prose drift risk. | |

**User's choice:** Append-only per phase; no stubs
**Notes:** Phase 3 owns only §1 + §2. Phase 4 owns §3. Phases 5/6 own §4 + §5. Phase 7 REL-03 owns top-level TOC + cross-section links + final consistency pass.

### Q4: Ready to write CONTEXT.md?

| Option | Description | Selected |
|--------|-------------|----------|
| I'm ready for context | Every gray area has captured decisions with rationale. | ✓ |
| Explore more gray areas | Surface 2-4 additional gray areas: US stable-pixel operational definition, supervisor EXPECTED_WALL_S, WorldCover/coastline data pipelines, MintPy vs linear-fit residual chain. | |

**User's choice:** I'm ready for context

---

## Claude's Discretion

Captured under the `<decisions>` Claude's Discretion subsection in CONTEXT.md:

- Exact SoCal 15-epoch sensing window (POEORB coverage, avoid S1B EOL)
- Residual-velocity computation chain (linear-fit start; MintPy promote-if-needed)
- US stable-pixel operational definition for CSLC-03 (subsideo stable_mask primary; OPERA-amp-stability report-alongside)
- Boxcar window size for per-IFG coherence (5×5 default; tunable if needed)
- AOIConfig / MojaveConfig dataclass shape (local-to-script default; promote if Phase 4 adopts)
- WorldCover fetch helper implementation (`data/worldcover.py` vs inline in stable_terrain.py)
- Coastline + water-body data source (Natural Earth vs OSM; start Natural Earth)
- Probe artifact query implementation (hand-run Python script per Phase 2 precedent)
- Supervisor EXPECTED_WALL_S budget (~16 h cap per script with per-AOI guards; 5 min warm re-run target)

## Deferred Ideas

Captured under the `<deferred>` section in CONTEXT.md:

- P2.4 isce3 minor-version kernel-change diagnostic experiment (LOW confidence, not a milestone gate)
- MintPy full SBAS inversion (linear-fit default; pyaps3 dependency surface avoidance)
- Stable_mask ∩ OPERA-amplitude-stability intersection (belt-and-braces, report-alongside)
- Tunable boxcar window size per AOI
- Shared AOIConfig / AOIResult in validation/eval_types.py
- Burst-DB-backed AOI catalogue (v2 scope)
- Mojave "fail fast + manual re-trigger" alternative fallback policy
- Residual velocity chain handling of POEORB→RESORB transition epochs
- Phase-coherence cross-check across isce3-equivalent-version stacks
- Natural Earth vs OSM for coastline + water-body geometries
- WorldCover fetch helper placement decision (plan-phase)
- Wet-vs-dry sensing-window test for Iberian drought-year signal (P5.4 adjacent)
- Retroactive extension of cell_status to Phase 2 RTC-EU cell (Phase 7 REL-01 consolidation)
