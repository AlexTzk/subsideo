# Phase 7: Results Matrix + Release Readiness - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 7 is the milestone closure test for v1.1 N.Am./EU Validation Parity & Scientific PASS.

**Deliverables:**

- **Matrix completeness (REL-01, REL-02, REL-05):** All 10 cells in `results/matrix.md` (5 products × 2 regions) render as PASS, FAIL-with-named-upgrade-path, DEFERRED-with-dated-unblock, or CALIBRATING-with-binds-v1.2 annotation. RTC:NAM currently renders as RUN_FAILED (missing sidecar); Phase 7 replaces this with a proper DEFERRED entry. CALIBRATING cells get inline `— binds v1.2` unblock annotation.
- **Methodology doc completion (REL-03):** `docs/validation_methodology.md` adds two new concise sections (~1 page each) covering OPERA UTC-hour frame selection and cross-sensor precision-first framing (both deferred from Phase 4/5 per §2.6 cross-reference table), then adds a top-level TOC and a final cross-section consistency pass. This satisfies all 4 REL-03 required findings.
- **Release closure (REL-05, REL-06):** Every cell labelled. `pytest` passes on macOS M3 Max as the final closure test.

**Not this phase:**
- TrueNAS Linux audit (REL-04) — deferred to v1.2; Dockerfile + Apptainer.def + env.lockfiles already exist at repo root.
- Re-running any heavy eval from scratch (RTC, CSLC, DISP, DIST, DSWx) — all sidecars are cached.
- Promoting any CALIBRATING gate to BINDING — that happens at v1.2 start per `binding_after_milestone` field on `Criterion` dataclasses.
- Tightening or relaxing any criterion threshold.
- New product capabilities or new OPERA product classes.

Phase 7 covers the 6 requirements mapped to it: **REL-01** (matrix all 10 cells filled), **REL-02** (manifest-driven matrix writer), **REL-03** (methodology doc 4 findings + distinction), **REL-04** (TrueNAS audit — DEFERRED), **REL-05** (all cells labelled), **REL-06** (pytest closure test).

</domain>

<decisions>
## Implementation Decisions

### RTC:NAM matrix cell (REL-01, REL-05)

- **D-01: Write `eval-rtc/metrics.json` with `cell_status='DEFERRED'` and `unblock_condition='v1.2 N.Am. RTC re-run'`.** The current matrix renders `RTC:NAM = RUN_FAILED (metrics.json missing)` because `run_eval.py` (the v1.0 N.Am. RTC script) was never migrated to write v1.1 harness sidecars. N.Am. RTC was not the focus of v1.1 (Phase 2 targeted EU RTC). Rather than fix the full harness migration, Phase 7 writes a minimal `eval-rtc/metrics.json` with DEFERRED status so the matrix_writer can render the cell correctly. The matrix_writer RTC:NAM branch must handle `cell_status='DEFERRED'` — it currently only handles `RUN_FAILED` (missing file) and numeric results. Unblock condition: v1.2 N.Am. RTC re-run (low effort; migration is harness.bounds_for_burst + metrics.json + meta.json write to run_eval.py).

- **D-02: Matrix renders RTC:NAM as `DEFERRED — N.Am. RTC not re-run in v1.1 (EU focus); unblock: v1.2 N.Am. harness migration`.** The matrix_writer RTC:NAM branch reads `cell_status` from the sidecar; when `'DEFERRED'`, renders the cell with the `unblock_condition` string inline. Consistent with how `dist:nam` renders `DEFERRED (CMR: operational_not_found)` — reuse the same rendering pattern.

### TrueNAS Linux audit (REL-04)

- **D-03: REL-04 DEFERRED to v1.2. macOS M3 Max is the v1.1 closure platform.** The Dockerfile, Apptainer.def, env.lockfile.linux-64.txt, and env.lockfile.osx-arm64.txt already exist at repo root (Phase 1 plan 01-09). No new infrastructure needed. Phase 7 documents REL-04 as DEFERRED in a brief release note or CHANGELOG entry with dated unblock: "Unblock: run `docker build` + `make eval-all` on TrueNAS Linux when homelab env is provisioned (v1.2)." `pytest` on macOS M3 Max satisfies REL-06 as the v1.1 closure test.

### validation_methodology.md finalization (REL-03)

- **D-04: Add two new concise top-level sections (§6 + §7), then add a TOC at the top of the document.** Per Phase 3 D-15 append-only policy; no existing sections are edited. Section numbering continues from §5 (DSWE).
  - **§6: OPERA frame selection by exact UTC hour + spatial footprint** — documents `harness.select_opera_frame_by_utc_hour()` rationale: OPERA reference products are selected by matching the exact acquisition UTC hour (not just date) to avoid comparing against acquisitions from a different ascending/descending pass geometry; spatial footprint overlap criterion prevents partial-coverage frames from contaminating the reference-agreement measurement. Policy statement: any eval script that selects an OPERA reference without UTC-hour + footprint matching is producing invalid reference-agreement numbers. ~1 page, same structural-argument → policy → code-pointer pattern as §1.
  - **§7: Cross-sensor comparison — precision-first framing (OPERA DIST vs EFFIS)** — documents why EFFIS-based DIST-S1 validation is inherently a cross-sensor precision-first comparison, not a recall-first comparison: EFFIS reports confirmed burnt-area polygons (final cumulative extent); DIST-S1 flags active disturbance signal at first-detection time. Precision-first means a high-precision / low-recall result from DIST-S1 against EFFIS is scientifically expected and should not be reported as a system failure unless precision itself collapses. Policy statement: cross-sensor evaluation results that show recall < 0.50 but precision > 0.70 are reported as "precision-first constraint satisfied; recall gap attributed to temporal class-definition mismatch (EFFIS final extent vs DIST first-detection)" — not as unqualified FAIL. ~1 page, same voice as §4.3 which already covers the class-definition mismatch caveat (§7 is the methodology-level framing; §4.3 is the implementation-level evidence).
  - **TOC:** added after the document header + preamble, before §1. Lists all 7 sections with anchor links. Phase 7 owns the TOC per ROADMAP REL-03 explicit "write the top-level table of contents".
  - **Consistency pass:** verify that §2.6 cross-reference table is updated to reflect §6 and §7 as "complete" (not "Phase N will append"). Update any stale forward-references in §3/§4 that pointed at Phase-4/Phase-5 future sections.

### CALIBRATING cells at milestone close (REL-05)

- **D-05: CALIBRATING cells that pass their gate get `— binds v1.2` appended inline in matrix.md.** Format: `*coh=X CALIBRATING — binds v1.2*`. This satisfies REL-05 strict reading (CALIBRATING with a dated unblock condition = deferred-with-dated-unblock). The matrix_writer must pass the `binding_after_milestone` value from `criteria.py` through to the cell render string — currently it italicises CALIBRATING cells but does not append the milestone. Planner should check whether `matrix_writer.py` already has this field plumbed or needs a one-line addition.

- **D-06: Data-point count confirmation before adding unblock annotation.** Phase 7 verifies counts from the existing matrix:
  - CSLC self-consistency: SoCal (t144_308029_iw1) + Mojave/Coso-Searles + Iberian/Meseta-North = **3 data points** → meets the ≥3 threshold from §2.5; eligible for v1.2 binding.
  - DISP self-consistency: SoCal + Bologna = **2 data points** → still below ≥3 threshold; must stay CALIBRATING at v1.2 too unless a third AOI is added. Phase 7 documents this in the CALIBRATING annotation: DISP cells read `*coh=X CALIBRATING — needs 3rd AOI before binding; see DISP_UNWRAPPER_SELECTION_BRIEF.md*`.

### Claude's Discretion

- Wave structure and plan count for Phase 7: the planner should determine the appropriate plan breakdown. Expected scope is small (2-4 plans): (1) RTC:NAM DEFERRED sidecar + matrix_writer fix + matrix.md regen; (2) validation_methodology.md §6 + §7 + TOC + consistency pass; (3) CALIBRATING cell annotations + matrix.md regen; (4) pytest closure + CHANGELOG/REL-04 deferral note. Plans may be combined if small.
- Exact content of §6 and §7: the researcher should ground these in the existing harness.py implementation and the Phase 4/5 CONCLUSIONS docs. The structural argument precedes the policy rule precedes the code pointer — standard doc voice.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/ROADMAP.md` §Phase 7 — goal, success criteria, REL-01 through REL-06 requirements list
- `.planning/REQUIREMENTS.md` §Results Matrix & Release Readiness — REL-01 through REL-06 requirement text

### Matrix framework (locked across phases)
- `results/matrix_manifest.yml` — 10-cell manifest; matrix_writer reads only this + sidecars (REL-02 lock)
- `src/subsideo/validation/matrix_writer.py` — matrix renderer; Phase 7 may add RTC:NAM DEFERRED branch + CALIBRATING `binds v1.2` annotation
- `src/subsideo/validation/criteria.py` — criterion registry with `CALIBRATING`/`BINDING` + `binding_after_milestone` field
- `results/matrix.md` — current state: RTC:NAM = RUN_FAILED; CSLC/DISP cells all CALIBRATING

### Methodology doc (Phase 7 appends §6 + §7 + TOC)
- `docs/validation_methodology.md` — append-only per Phase 3 D-15; §1 cross-version phase impossibility; §2 product-quality vs RA distinction (incl. §2.6 cross-reference table with deferred items); §3 DISP adapter; §4 DIST methodology; §5 DSWE F1 ceiling; Phase 7 adds §6 + §7 + TOC
- `src/subsideo/validation/harness.py` — `select_opera_frame_by_utc_hour()` for §6 content grounding
- `src/subsideo/validation/effis.py` — EFFIS cross-sensor framing for §7 content grounding

### CALIBRATING data points (for D-06 verification)
- `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` — SoCal + Mojave/Coso-Searles data points
- `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` — Iberian/Meseta-North data point
- `CONCLUSIONS_DISP_N_AM.md` — SoCal DISP self-consistency
- `CONCLUSIONS_DISP_EU.md` — Bologna DISP self-consistency

### Deferred infrastructure (already exists — do not recreate)
- `Dockerfile` — Phase 1 plan 01-09 deliverable; exists at repo root
- `Apptainer.def` — Phase 1 plan 01-09 deliverable; exists at repo root
- `env.lockfile.linux-64.txt` — Phase 1 plan 01-09 deliverable; exists at repo root
- `env.lockfile.osx-arm64.txt` — Phase 1 plan 01-09 deliverable; exists at repo root

### Prior phase CONTEXT for carry-forward decisions
- `.planning/phases/06-dswx-s2-n-am-eu-recalibration/06-CONTEXT.md` — D-15 (named_upgrade_path field on DswxCellMetrics); D-21 (CONCLUSIONS structure)
- `.planning/phases/03-cslc-s1-self-consistency-eu-validation/03-CONTEXT.md` — D-15 append-only policy for validation_methodology.md

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/subsideo/validation/matrix_writer.py` — existing dispatch branches for all products; Phase 7 extends RTC:NAM branch to handle `cell_status='DEFERRED'` and adds `binding_after_milestone` annotation to CALIBRATING cell renders
- `src/subsideo/validation/criteria.py` — `binding_after_milestone` field already present on `Criterion` dataclass; Phase 7 reads this field in matrix_writer
- `eval-dist/metrics.json` — exemplar for DEFERRED sidecar format: `cell_status='DEFERRED'`, `unblock_condition=...`, `cmr_probe_outcome=...`; use this as the template for the new `eval-rtc/metrics.json`

### Established Patterns
- DEFERRED sidecar pattern (Phase 5 D-16): `cell_status='DEFERRED'` + `unblock_condition` string in metrics.json; matrix_writer reads and renders inline. Phase 7 re-uses this for RTC:NAM.
- Append-only methodology doc (Phase 3 D-15): never edit existing sections; only append new top-level sections. Phase 7 adds §6 + §7 + TOC (TOC is prepended before §1, which is the one exception to append-only since it's a navigational element).
- CALIBRATING italics rendering (Phase 1 D-03 / GATE-04): `*...*` markdown for CALIBRATING cells in matrix.md. Phase 7 extends to `*... CALIBRATING — binds v1.2*` pattern.

### Integration Points
- `results/matrix.md` is generated by `make eval-all` → matrix_writer reads manifest + sidecars → writes matrix.md. Phase 7 triggers `make eval-all` after writing the RTC:NAM sidecar and any matrix_writer changes.
- `eval-rtc/` directory: currently lacks `metrics.json` and `meta.json`. Phase 7 writes a minimal DEFERRED metrics.json; meta.json should also be written (git SHA + input content hashes per ENV-09).

</code_context>

<specifics>
## Specific Ideas

- **RTC:NAM DEFERRED sidecar format**: model after `eval-dist/metrics.json` (`cell_status='DEFERRED'`, `unblock_condition=...`). The matrix_writer RTC:NAM dispatch branch currently calls `_render_rtc_cell()`; add a DEFERRED guard at the top of that function (or in the dispatch logic) that returns the DEFERRED string when `cell_status == 'DEFERRED'`.
- **DISP CALIBRATING annotation specificity**: unlike CSLC (which hits 3 data points), DISP needs a 3rd AOI. The DISP cell annotation should reference `DISP_UNWRAPPER_SELECTION_BRIEF.md` as the follow-up context — the brief already scopes v1.2 DISP work, and a 3rd AOI self-consistency eval would naturally accompany the unwrapper selection milestone.
- **validation_methodology.md §6 and §7 voice**: same pattern as §1 (structural argument → policy statement → code pointer → diagnostic evidence appendix). §6 should cite `harness.select_opera_frame_by_utc_hour` by function signature. §7 should cross-reference §4.3 (EFFIS class-definition mismatch caveat) rather than duplicating it.

</specifics>

<deferred>
## Deferred Ideas

- **TrueNAS Linux full eval re-run** — REL-04 deferred to v1.2. Unblock: provision TrueNAS Linux dev container, run `docker build -f Dockerfile .` + `make eval-all` with pre-cached sidecars synced via rsync. Estimated cold-env: <12 h on x86-64 Linux with cached SAFE/HDF5 data. Infrastructure (Dockerfile, Apptainer.def, lockfile) already committed.
- **run_eval.py full harness migration (RTC:NAM)** — the proper fix is to migrate `run_eval.py` to use `validation.harness` and write v1.1 compliant sidecars, then actually re-run the N.Am. RTC eval to get live numbers. Deferred to v1.2; low effort when it's time.
- **DISP 3rd AOI self-consistency** — needed to promote DISP self-consistency gates from CALIBRATING to BINDING. Deferred to the DISP Unwrapper Selection follow-up milestone (v1.2); see `DISP_UNWRAPPER_SELECTION_BRIEF.md` for scoping.

</deferred>

---

*Phase: 7-results-matrix-release-readiness*
*Context gathered: 2026-04-28*
