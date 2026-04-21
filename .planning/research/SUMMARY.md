# Research Summary — subsideo v1.1 (N.Am./EU Validation Parity & Scientific PASS)

**Project:** subsideo v1.1 — validation-hardening milestone on a shipped v1.0 codebase
**Domain:** SAR/InSAR/optical validation framework layered on an OPERA-equivalent geospatial library
**Researched:** 2026-04-20
**Confidence:** HIGH (every non-trivial claim verified against PyPI/conda-forge metadata, shipped v1.0 source, or v1.0 CONCLUSIONS docs; LOW-confidence items explicitly called out)

**Source research files:**
- `.planning/research/STACK.md` — v1.1 stack deltas against v1.0
- `.planning/research/FEATURES.md` — table-stakes / differentiators / anti-features
- `.planning/research/ARCHITECTURE.md` — module placement on top of shipped v1.0 tree
- `.planning/research/PITFALLS.md` — metrics-vs-targets discipline + phase-specific traps
- `BOOTSTRAP_V1.1.md` — source-of-truth scope (delta corrections surfaced below)

---

## Executive Summary

v1.1 is **not** a feature milestone — it is a validation-hardening milestone on top of a shipped v1.0 pipeline. The five product pipelines already run; what v1.1 delivers is the structural discipline that turns ad-hoc per-script evals into a reproducible results matrix, plus the eval coverage (RTC-EU, CSLC-EU, DSWx-N.Am., DIST LA-T11SLT) that v1.0 never executed. The milestone's own closure test (`fresh clone → micromamba env create → make eval-all → filled matrix`) is the north star for every scoping decision below.

The central methodological axis is BOOTSTRAP's **metrics-vs-targets** framing: reference-agreement (subsideo vs OPERA/EGMS/JRC) is a sanity check that does not tighten; product-quality (self-consistency, ground-truth residuals, F1) is the gate. Research converted this framing into a structural guardrail set — an immutable `criteria.py`, split `ProductQualityResult` / `ReferenceAgreementResult` dataclasses, two-column matrix output, and a `tests/product_quality/` vs `tests/reference_agreement/` split — because "be careful" does not survive contact with a green CI run. The roadmapper should treat these guardrails as Phase 0 deliverables equal in weight to BOOTSTRAP §0.1–0.7, not as Phase 6 nice-to-haves.

The scientific risk profile is bimodal. Low-risk phases: 1 (RTC-EU, deterministic), 4 (DIST with config-drift gate already correctly scoped). Medium-risk phases: 2 (CSLC self-consistency — first rollout of a new product-quality gate; stable-terrain mask contamination + reference-frame alignment are real and currently underspecified in BOOTSTRAP), 3 (DISP — "PHASS planar ramp" attribution may lump orbit/tropospheric/ionospheric sources into the same label, so a ramp-attribution diagnostic must precede the hand-off to the DISP Unwrapper Selection follow-up). High-risk phase: 5 (DSWx recalibration — fit-set quality caps F1 regardless of grid-search quality; JRC labelling noise and drought-year wet/dry pairing can silently contaminate). Research confidence is HIGH on the corrections surfaced below, MEDIUM on the coherence-gate definition and JRC contamination rates because those depend on empirical measurement on subsideo's stacks, not yet run.

---

## BOOTSTRAP corrections surfaced by research

These are **deltas from BOOTSTRAP_V1.1.md** that the roadmapper must fold into the roadmap. BOOTSTRAP is the source-of-truth scope; research confirmed that scope but found four specific instructions that are either wrong or underspecified.

| Item | BOOTSTRAP says | Research finding | Correction |
|------|---------------|------------------|------------|
| **tophu install channel** (§0.2) | "Add tophu to `conda-env.yml`'s `pip:` block" | tophu is not on PyPI (`pip install tophu` returns 404); it is conda-forge only. Dolphin's `multiscale_unwrap()` path (triggered by `UnwrapMethod.PHASS` — our production config) imports tophu deferred-at-first-call, so the asserted regression test `from dolphin.unwrap import run` **does not verify the fix** (that import succeeds without tophu). | STACK §2 — install via `- tophu=0.2.1` in top-level `dependencies:` block. Regression test is `import tophu` (not the dolphin import). |
| **rio-cogeo root cause** (§0.3) | "Three product files tripped over the rio-cogeo 7.x `cog_validate` move" | `cog_validate` has lived at both `rio_cogeo.cogeo.cog_validate` and top-level `rio_cogeo.cog_validate` since 2.1.1 (2021). **There was no API move in 7.x.** The defensive `try/except` was debugging a different symptom — likely rio-cogeo 7.x dropping Python 3.10 support (subsideo targets 3.10+). | STACK §3 — pin `rio-cogeo==6.0.0` (do NOT jump to 7.x), centralise on root-level re-exports through `src/subsideo/_cog.py`, remove the defensive try/except. |
| **macOS fork mitigation** (§0.4) | "`multiprocessing.set_start_method('fork', force=True)` on macOS" + "watchdog that aborts after 2× expected wall time" | Fork mode alone is insufficient. Four additional failure modes will bite in `make eval-all`: (1) Cocoa/matplotlib state corruption, (2) CFNetwork HTTPS session pool corruption, (3) FD-limit (macOS default 256, isce3/dolphin/dist-s1 easily exceed), (4) joblib/loky fork deprecation. | PITFALLS P0.1 — `_mp.configure_multiprocessing()` must also set `MPLBACKEND=Agg`, raise `RLIMIT_NOFILE` to 4096, close cached `requests.Session` objects pre-fork, and fall through to `forkserver` on Python ≥3.14. Watchdog must be subprocess-level (not thread/signal) with `os.killpg` for grandchild cleanup. |
| **bounds_for_burst placement** (§0.6) | "Programmatic DEM bounds" as a separate Phase 0.6 module | `opera_utils.burst_frame_db.get_burst_id_geojson()` already exposes this programmatically. The helper is eval-script-shared plumbing, not a new module — it collapses into `validation/harness.py` (§0.5). | ARCHITECTURE §1 — add `bounds_for_burst()` as a fifth function on `harness.py`. Collapses BOOTSTRAP's 0.5/0.6 into a single "harness complete" gate. |

**Additional structural guardrails (not in BOOTSTRAP, research recommends as Phase 0 deliverables):**

| Guardrail | Why Phase 0, not later | Source |
|-----------|------------------------|--------|
| `src/subsideo/validation/criteria.py` — immutable module with `CALIBRATING` vs `BINDING` distinction, `binding_after_milestone: str` field on calibrating gates | BOOTSTRAP's "metric becomes target" framing is social; without a code-level choke point (reviewed immutability, CI enforcement at milestone start), every phase's PR is a drift opportunity. | PITFALLS M1, M5, M6 |
| Split `ProductQualityResult` / `ReferenceAgreementResult` dataclasses; no top-level `.passed` that collapses the two | Every `run_eval_*.py` and every matrix cell reports both; if the split lives only in prose (not code), the next refactor silently collapses it. | PITFALLS M2 |
| Two-column matrix output (`Product-quality gate` / `Reference-agreement`), CALIBRATING cells marked distinctly | Matrix generator is the choke point — if it writes one column, every downstream reader conflates. | PITFALLS M2 |
| `tests/product_quality/` (asserts values) vs `tests/reference_agreement/` (asserts plumbing only) directory split | Reference-agreement assertions in CI create the exact feedback loop BOOTSTRAP wants to avoid (CI fail → tighten/loosen → drift). Directory naming makes the discipline reviewable. | PITFALLS M3 |
| Shared `src/subsideo/validation/stable_terrain.py` + `selfconsistency.py` — built once in **Phase 0.5.5**, consumed by Phase 2 AND Phase 3 | BOOTSTRAP places these inside Phase 2; if Phase 2 slips, Phase 3 inherits the slip. Building them as the last step of Phase 0 removes the dependency. | FEATURES Dependency notes + PITFALLS P2.1, P2.3 |

---

## Phase 0 expansion — what it actually delivers

BOOTSTRAP §0.1–0.7 specifies seven deliverables. Research found Phase 0 must also deliver the following for the milestone's guardrails to be load-bearing.

| # | Deliverable | Source | Reuse downstream |
|---|-------------|--------|------------------|
| 0.1 | numpy<2 pin + remove 4 monkey-patches in `src/subsideo/products/cslc.py` | BOOTSTRAP §0.1, STACK §1 | All phases |
| 0.2 | tophu via **conda-forge** (NOT pip); regression test is `import tophu` | STACK §2 correction to BOOTSTRAP §0.2 | Phase 3 |
| 0.3 | `src/subsideo/_cog.py` with `rio-cogeo==6.0.0` root-level re-exports + `ensure_valid_cog()` that re-translates post-metadata-injection | STACK §3 correction to BOOTSTRAP §0.3; PITFALLS P0.3 | Phase 1, Phase 5 |
| 0.4 | `src/subsideo/_mp.py` — full fork bundle: start method + MPLBACKEND + ulimit + session close + forkserver fallback. Subprocess-level watchdog with `os.killpg`. | PITFALLS P0.1 expands BOOTSTRAP §0.4 | Phase 3, Phase 4, Phase 6.3 |
| 0.5 | `src/subsideo/validation/harness.py` — 5 functions including `bounds_for_burst` (collapsed from §0.6); per-source retry policies | FEATURES §0; ARCHITECTURE §1; PITFALLS P0.4, P4.3 | Every eval script |
| 0.5.5 | `src/subsideo/validation/stable_terrain.py` + `selfconsistency.py` (WorldCover+slope+coastline+water buffers; mean/median/p25/p75 coherence + persistently-coherent fraction + reference-frame-aligned residual velocity) | FEATURES dependency notes; PITFALLS P2.1, P2.2, P2.3 | Phase 2, Phase 3 |
| 0.6a | `validation/criteria.py` with `CALIBRATING`/`BINDING` + `binding_after_milestone` | PITFALLS M1, M5, M6 | Every compare_*.py; matrix |
| 0.6b | Split `*ValidationResult` into `product_quality` / `reference_agreement` | PITFALLS M2 | Every eval + matrix |
| 0.6c | `tests/product_quality/` vs `tests/reference_agreement/` split | PITFALLS M3 | All Phase 1–5 tests |
| 0.7 | `Makefile` with per-cell subprocess isolation, failure isolation, `meta.json` per-eval with git SHA + content hashes | BOOTSTRAP §0.7; PITFALLS R1, R2, R3 | Phase 6 |
| 0.8 | `results/matrix_manifest.yml` + `matrix_schema.py` pydantic model | ARCHITECTURE §6 | Phase 6.1 |
| 0.9 | `env.lockfile.txt` committed; Dockerfile / Apptainer recipe | PITFALLS P0.2, R4 | Phase 6.3, CI |

**Phase 0 internal ordering** (ARCHITECTURE §Build Order): 0.1 → 0.3 → 0.4 → 0.5+0.5.5 → 0.6abc → 0.2 → 0.7+0.8+0.9.

---

## Key Findings

### Recommended Stack (delta-only; v1.0 stack unchanged)

Full rationale in STACK.md. v1.1 adds:
- `numpy<2.0` pinned (compass/s1-reader/isce3 lack numpy-2 as of 2026-04-20)
- `tophu=0.2.1` via conda-forge — **not pip**
- `rio-cogeo==6.0.0` — do NOT jump to 7.x (drops Python 3.10)
- `tenacity==9.1.4` (CloudFront+ASF+CDSE retry)
- `owslib==0.35.0` (EFFIS WFS; no pyeffis exists)
- `optuna==4.8.0` optional (Phase 5.3 restart-safe grid search; stdlib fallback adequate)
- `dist-s1` 2.0.14, `asf-search` 12.0.7 (trivial patch bumps)

**Explicitly rejected:** `pip install tophu` (doesn't exist), `rio-cogeo==7.x`, `richdem`/`xdem`/`whitebox` (GDAL already present), `terracatalogueclient` (VITO heavyweight), `just`/`taskfile.dev` (break closure test), `pebble.ProcessPool` as primary watchdog.

### Expected Features

**Must have** (closure-blocking): See Phase 0 expansion + Phase 1–6 watch-outs below.

**Should have** (differentiators): Coloured+JSON dual preflight output; versioned metrics.json schema; `make eval-all` summary line + trendline diff; py-spy dump on watchdog abort; chained `prior_dist_s1_product` run (if Phase 0.4 resolves hang).

**Defer (v2+):** ML-based DSWE replacement, global expansion, multi-burst mosaicking, CR absolute radiometric accuracy for RTC, GNSS-residual comparison for CSLC, `conda-lock` pinning.

### Anti-features (explicitly excluded — 15 total)

The 4 from BOOTSTRAP plus 11 surfaced by research. Roadmapper must carry forward so they don't re-enter as scope creep:

1. Picking production DISP unwrapper (spun out)
2. ML-based DSWE replacement (v1.1 upgrade path, not v1.1 scope)
3. Relaxing DSWx F1 > 0.90 bar
4. Multi-burst mosaicking / cross-burst consistency — v2
5. New OPERA product classes (DSWx-S1, DSWx-HLS) — v2
6. Global expansion beyond N.Am. + EU — v2
7. Gaussian-weighted or Lanczos multilooking in `prepare_for_reference` by default *(subtlety: PITFALLS P3.1 argues Gaussian σ=0.5×ref is physically correct when reference is itself Gaussian-smoothed — flagged as Phase 3 ADR, not accepted either way)*
8. Writing comparison-adapter output back to the product (validation-only)
9. New `subsideo validate-dist-la` CLI subcommand
10. README PASS/FAIL badge
11. Re-running RTC EU with tighter criteria because N.Am. nailed 0.045 dB (M1 target-creep)
12. Tightening CSLC residual velocity from 5 mm/yr during Phase 2
13. Interactive AOI picker UI for Phase 5
14. Medium post / external publication
15. Docker release as distribution channel (Dockerfile for CI/reproducibility only)

### Architecture Approach

Full rationale in ARCHITECTURE.md.

**Major placements (v1.1 deltas on v1.0):**
1. `_cog.py`, `_mp.py` as top-level private modules (follow `_metadata.py` precedent). NOT `utils/`.
2. `validation/harness.py` as single file (~300–400 LOC; promote to package at ~600+ LOC).
3. `prepare_for_reference()` extends `validation/compare_disp.py` — do NOT create `validation/adapters.py` (speculative generality).
4. DSWx thresholds in `products/dswx_thresholds.py` (typed NamedTuple + pydantic-settings region selector) — not YAML/JSON.
5. Eval scripts stay at repo root (9 + 6 new = 15; move threshold is ~25).
6. `results/matrix.md` via explicit `matrix_manifest.yml` + per-eval `metrics.json` sidecars — never glob-parse CONCLUSIONS.
7. Cache dirs stay as `eval-*/` siblings at repo root (gitignored).

**Forbidden imports:** `products/*` → `validation/*` (cycle); `_cog`/`_mp` → any `subsideo.*` (must be leaves); `utils/*` → `products/*`/`validation/*` (inversion); `validation/harness` → `products/*`.

### Critical Pitfalls (full taxonomy in PITFALLS.md)

**M-series (metrics-vs-targets, 6 pitfalls):** M1 target-creep via reference-score anchoring; M2 single-`passed` conflation; M3 reference-agreement silently becomes CI gate; M4 product-quality relaxation (F1>0.90 bar); M5 new-gate too-tight definition at first encounter; M6 perpetual CALIBRATING. All six require code-level structural guardrails in Phase 0.6abc.

**P-series phase-specific (13 pitfalls, top 5 by impact):**
- **P0.1** macOS fork mode insufficient alone (Cocoa/CFNetwork/FD-limit/loky)
- **P2.1/P2.2/P2.3** self-consistency gate underspecified (WorldCover contamination; mean-vs-median choice; reference-frame alignment)
- **P3.2** "PHASS planar ramp" lumps 4 sources (PHASS/troposphere/orbit/ionosphere); ramp-attribution diagnostic required
- **P4.1/P4.2** DIST config-drift extraction needs explicit 7-key list; single-tile F1 variance needs block-bootstrap CI
- **P5.1/P5.2** DSWE grid-search overfit; JRC labelling noise

**R-series (5 pitfalls):** cache invalidation under-specified (R1); parallel eval write races (R2); failure isolation — one eval stages matrix (R3); reproducibility-claim drift (R4); CONCLUSIONS vs methodology-doc drift (R5).

---

## Implications for Roadmap

Research validates BOOTSTRAP's six-phase structure. Adopt phase boundaries as-is with Phase 0 expansion above.

### Phase 1 (GSD) — Environment hygiene, framework consolidation, **and guardrail scaffolding** (BOOTSTRAP Phase 0)
**Rationale:** Every subsequent phase calls at least one Phase 0 helper. Guardrail modules must land in Phase 0, not scattered across Phases 2/3/6.
**Delivers:** 9 modules + Makefile + matrix manifest + env lockfile + Dockerfile.
**Watch out for:** P0.1, P0.2, P0.3, P0.4, M1–M6.
**Effort:** 4–5 days (BOOTSTRAP said 3–4; +1 for guardrails).

### Phase 2 (GSD) — RTC-S1 EU validation (BOOTSTRAP Phase 1)
**Rationale:** Lowest-risk; first user of Phase 0 harness as proof-out.
**Delivers:** 3–5 EU RTC bursts PASS; terrain-regime-coverage table.
**Watch out for:** P1.1 (at least one >1000 m relief AND one >55°N mandatory).
**Effort:** 2 days.

### Phase 3 (GSD) — CSLC self-consistency + EU validation (BOOTSTRAP Phase 2)
**Rationale:** Introduces first NEW product-quality gate; exercises Phase 0.5.5 modules.
**Delivers:** 3 eval scripts, 3 CONCLUSIONS, methodology cross-version section.
**Watch out for:** P2.1, P2.2, P2.3, P2.4, M5 (first rollout is CALIBRATING not BINDING).
**Effort:** 4–5 days.

### Phase 4 (GSD) — DISP comparison adapter + honest FAIL (BOOTSTRAP Phase 3)
**Rationale:** Scope contracted — unwrapper selection spun to follow-up milestone.
**Delivers:** `prepare_for_reference` adapter with explicit `method=` arg; self-consistency gate; ramp-attribution diagnostic; DISP Unwrapper Selection brief.
**Watch out for:** P3.1 (multilook method default is Phase 4 decision — PITFALLS and FEATURES disagree, roadmapper must flag), P3.2 (no "PHASS FAIL" label without ramp-attribution), M2.
**Effort:** 3 days.

### Phase 5 (GSD) — DIST OPERA v0.1 + EFFIS EU (BOOTSTRAP Phase 4)
**Rationale:** N.Am. flips from "deferred" to "v0.1 comparison with config-drift gate."
**Delivers:** LA T11SLT comparison or deferral; CMR probe; EFFIS cross-validation; +1 EU event.
**Watch out for:** P4.1, P4.2, P4.3, P4.4, P4.5.
**Effort:** 3–4 days.

### Phase 6 (GSD) — DSWx N.Am. positive control + EU recalibration (BOOTSTRAP Phase 5)
**Rationale:** Largest phase, largest schedule risk. AOI research (3–4 days) must precede compute.
**Delivers:** N.Am. positive control; AOI selection notebook; 12-pair fit set; grid search; frozen constants; reproducibility notebook; EU re-run.
**Watch out for:** P5.1 (LOO-CV gap <0.02), P5.2 (JRC pre-screen + shoreline exclusion), P5.3 (DSWE ceiling citation), P5.4 (drought-year wet/dry ratio), M4 (F1>0.90 bar DOES NOT MOVE).
**Effort:** 5–7 days.

### Phase 7 (GSD) — Results matrix, methodology doc, release audit (BOOTSTRAP Phase 6)
**Rationale:** Terminal phase; closure-test artifact is milestone goal #1.
**Delivers:** `results/matrix.md`; `docs/validation_methodology.md`; TrueNAS audit; env lockfile + Dockerfile committed.
**Watch out for:** R1, R2, R3, R4, R5.
**Effort:** 2 days.

### Phase Ordering Rationale
- Phase 1 (GSD) must land first; guardrails within Phase 1, not later.
- Phase 3 + Phase 4 share `stable_terrain.py` + `selfconsistency.py` — build once in Phase 1.
- Phase 6 AOI research precedes compute.
- Single developer serial = 22–28 days; two developers split DISP+DSWx from RTC+CSLC+DIST post-Phase-1.

### Research Flags

**Needs `/gsd:research-phase` during planning:**
- **Phase 3 (CSLC)** — `stable_terrain.py` exclusion details; coherence metric choice (mean/median/persistently-coherent). MEDIUM uncertainty.
- **Phase 4 (DISP)** — Multilook method default (PITFALLS P3.1 Gaussian vs FEATURES anti-feature-table simple block-mean — in tension); ramp-attribution diagnostic thresholds.
- **Phase 6 (DSWx)** — AOI research is a first-class sub-task inside the phase, not planning.

**Standard patterns (skip research-phase):**
- **Phase 1 (env)** — mechanical; everything already specified.
- **Phase 2 (RTC EU)** — fork of existing `run_eval.py`.
- **Phase 5 (DIST)** — BOOTSTRAP §4 + PITFALLS P4.1–P4.5 give exact prevention.
- **Phase 7 (release)** — mechanical aggregation.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI/conda-forge 2026-04-20; 4 BOOTSTRAP corrections grounded in source-code inspection |
| Features | HIGH | Every feature grounded in BOOTSTRAP; 14 anti-features extend BOOTSTRAP's 4 |
| Architecture | HIGH | Every placement tied to existing v1.0 convention |
| Pitfalls M-series | HIGH | Code-level structural guardrails, not "be careful" |
| Pitfalls P-series | HIGH on P0.1–P0.4, P3.1, P3.2, P4.1–P4.5; MEDIUM on P2.1, P2.2 (literature-backed, empirical verification pending); LOW on P2.4 isce3 minor-version diagnostic |
| Pitfalls R-series | HIGH | All five observable-under-scale; R4 already visible in v1.0 |

**Overall confidence:** HIGH on stack/architecture/milestone shape/BOOTSTRAP corrections. MEDIUM on empirical calibration choices (coherence gate definition, DSWE ceiling) — explicitly named as Phase 3/6/7.2 calibration deliverables, not pre-commitments.

### Gaps to Address (carry to phase planning)

1. **Coherence metric choice** for CSLC self-consistency gate — mean/median/persistently-coherent; pre-commit before SoCal calibration (Phase 3 planning).
2. **DISP multilook method default** — PITFALLS P3.1 (Gaussian) vs FEATURES anti-features (block-mean) in direct tension. Roadmapper must mark as Phase 4 decision requiring ADR.
3. **DSWE F1 ≈ 0.92 ceiling citation chain** — verify at PROTEUS ATBD source or fall back to "our own 6-AOI bound." Phase 6/7.2 prerequisite.
4. **isce3 minor-version phase-coherence experiment** — PITFALLS P2.4 proposes 0.19 vs 0.25 + 0.25.8 vs 0.25.10 diagnostic. Optional methodology enhancement, not milestone gate. LOW confidence.
5. **Reference-frame alignment operational definition** — common-stable-PS-set intersection rule (min count, proximity buffer, outlier handling) is Phase 3 methodological decision.
6. **Chained `prior_dist_s1_product` run feasibility** — depends on whether Phase 1 _mp.py bundle resolves dist-s1 hang. Optional either way.
7. **TrueNAS audit scope** — FEATURES §Phase 6 lists 6 in-scope hazards + Windows/WSL2 out-of-scope. Carry into Phase 7 planning.

---

## Sources

### Primary (HIGH confidence)
- `BOOTSTRAP_V1.1.md` — source-of-truth scope
- `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md` — 2026-04-20 verified
- Shipped v1.0 source: `src/subsideo/_metadata.py`, `validation/compare_*.py`, 9 `run_eval_*.py`, `products/*.py`
- v1.0 CONCLUSIONS: `CONCLUSIONS_CSLC_N_AM.md` §5, `CONCLUSIONS_DISP_N_AM.md` §5, `CONCLUSIONS_DSWX.md` §3, `CONCLUSIONS_DIST_EU.md`

### Secondary (MEDIUM confidence)
- ESA WorldCover 2021 Product Validation Report v2.0 — class 60 European accuracy
- JRC Global Surface Water accuracy characterization — commission/omission + shoreline ambiguity
- joblib/loky fork deprecation + cpython #84559 — macOS fork-vs-threads
- EFFIS WFS endpoint — 2026 schema unverified; layer names drift
- OPERA DSWx-HLS ATBD / PROTEUS — 0.92 ceiling cited but not directly extracted

### Tertiary (LOW confidence)
- PITFALLS P2.4 isce3 minor-version kernel-change diagnostic — proposed experiment, no empirical data
- 0.7 coherence threshold on stable terrain — BOOTSTRAP's sensible starting bar; ±0.1 uncertainty without SoCal calibration

---

*Research completed: 2026-04-20*
*Ready for roadmap: yes*
