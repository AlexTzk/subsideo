# Phase 5: DIST-S1 OPERA v0.1 + EFFIS EU - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 05-dist-s1-opera-v0-1-effis-eu
**Areas discussed:** Config-drift gate, N.Am. AOI + bootstrap CI, EU events orchestration + chained retry, CMR supersede + EFFIS rasterisation

---

## Gray Area Selection

**Question:** Which gray areas do you want to discuss for Phase 5 (DIST-S1 OPERA v0.1 + EFFIS EU)? Pick any combination.

| Option | Description | Selected |
|--------|-------------|----------|
| Config-drift gate (DIST-02, P4.1) | Where the 7 keys come from in OPERA v0.1 sample; failure-mode if metadata incomplete; what threshold counts as 'material delta'. Drives whether the cell PASSES, DEFERS, or BLOCKS. | ✓ |
| N.Am. AOI + bootstrap CI (DIST-01, DIST-03) | v1.0 Park Fire 10TFK vs DIST-01-mandated T11SLT disposition; bootstrap helper location; CI schema; 1km-block boundary handling. | ✓ |
| EU events orchestration + chained retry (DIST-06, DIST-07) | 3-event aggregate cell vs 3 cells; existing-script disposition; chained prior_dist_s1_product workflow scope; pass criterion. | ✓ |
| CMR supersede + EFFIS rasterisation (DIST-04, DIST-05, P4.4) | CMR probe wiring location; supersede semantics; EFFIS rasterisation default; WFS retry policy. | ✓ |

**User's choice:** All 4 areas selected.

---

## Config-drift gate (DIST-02, P4.1)

### Q1: Metadata extraction strategy when canonical HDF5 attrs are absent

| Option | Description | Selected |
|--------|-------------|----------|
| HDF5 attrs only — fail loudly if missing | Canonical path; if keys missing, raise ConfigDriftMetadataError; matrix renders BLOCKER. Aligns with PITFALLS R-series (no silent best-effort). | |
| Attrs primary + JSON-string fallback | Try HDF5 attrs first; if absent, parse known JSON-string locations. Fall through to BLOCKER only if both fail. More forgiving but writes more code. | |
| Defer to plan-phase — probe sample first | Plan-phase fetches OPERA v0.1 sample, runs h5dump -A to surface actual structure, then commits extraction strategy with evidence. Lowest-risk — no guessing about a pre-operational artefact's metadata layout. | ✓ |

**User's choice:** Defer to plan-phase — probe sample first
**Rationale captured in D-01:** PITFALLS P4.1 explicitly warns this is unknowable from spec alone — "pre-operational products often have incomplete metadata"; mirrors Phase 4 D-Claude's-Discretion pattern (defer artefact-evidence-dependent specifics to plan-phase).

### Q2: Lock the 7 key parameters now or in plan-phase

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to plan-phase | Plan-phase researches dist-s1 2.0.14 source + OPERA v0.1 sample to commit all 7 with evidence. Phase 4 D-Claude's-Discretion pattern. Lowest target-creep risk. | ✓ |
| Lock 5 now + 2 discoverable | 5 named in DIST-02 are locked; 2 'further' parameters discovered during plan-phase research. | |
| Claude probes now and locks all 7 | Spawn quick research probe in this discuss session; lock in CONTEXT.md. Faster but adds unplanned subagent invocation. | |

**User's choice:** Defer to plan-phase
**Rationale captured in D-02:** dist-s1 2.0.14 source + sample evidence both required for credible commit; PITFALLS P4.1 candidates list is non-exhaustive.

### Q3: Material-delta threshold semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Any difference → defer | Strictest. Prevents target-creep (M1). Aligned with milestone discipline 'validators not quality ceilings'. Matrix-cell semantics clean: PASS / FAIL / DEFERRED. | ✓ |
| Per-key tolerance bands (locked at plan-phase) | Some keys binary, some numeric; plan-phase commits exact bands with rationale. More interpretive. | |
| Algorithm-structure-only → defer | Defer only when key changes algorithm structure. Most permissive; introduces silent-pass attack surface. | |

**User's choice:** Any difference → defer
**Rationale captured in D-03:** Cleanest matrix-cell semantics + M1 anti-target-creep + per-key tolerances introduce uneditable interpretation pressure.

---

## N.Am. AOI + bootstrap CI (DIST-01, DIST-03)

### Q1: v1.0 Park Fire (10TFK) vs DIST-01-mandated T11SLT disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Replace 10TFK with T11SLT | eval-dist/ rewritten with T11SLT outputs; CONCLUSIONS_DIST_N_AM.md gets v1.1 sections appended with v1.0 Park Fire as 'v1.0 historical baseline' preamble. | |
| Keep both as 2-AOI aggregate cell | N.Am. cell renders as aggregate over [10TFK Park Fire (no-ref deferred), T11SLT v0.1]. Phase 2 RTC-EU pattern. Adds 'no-reference' as per-AOI status. Muddier. | |
| Keep Park Fire as separate non-matrix artifact | T11SLT occupies dist:nam matrix cell. Park Fire stays in eval-dist-park-fire/ (rename) as historical artifact — v1.0 CONCLUSIONS readable but no manifest entry. Clean matrix; preserves v1.0 work intact. | ✓ |

**User's choice:** Keep Park Fire as separate non-matrix artifact
**Rationale captured in D-05:** Park Fire was structurally-complete-no-comparison (no F1); doesn't enter matrix; rename preserves cache + run.log + opera_reference/ intact; CONCLUSIONS_DIST_N_AM.md preserves Park Fire content as v1.0 baseline preamble (Phase 4 D-13 pattern).

### Q2: Block-bootstrap helper module location

| Option | Description | Selected |
|--------|-------------|----------|
| Extend validation/metrics.py | metrics.py already houses bias, rmse, correlation. Single import surface. | |
| New validation/bootstrap.py | Clean separation — bootstrap is methodology, not metric. Easier to reuse for non-F1 metrics. Adds one more module. | ✓ |
| Extend validation/selfconsistency.py | selfconsistency.py is the 'methodology' module; mixes product-quality with reference-agreement concerns. | |

**User's choice:** New validation/bootstrap.py
**Rationale captured in D-06:** Clean separation; reusable for non-F1 metrics (bias CI in DSWx Phase 6 if needed); module-level constants auditable.

### Q3: CI schema in metrics.json

| Option | Description | Selected |
|--------|-------------|----------|
| F1 + ci_lower + ci_upper (95%) | Point estimate plus 95% bounds for each metric. Matches ROADMAP '95% CI' phrasing. Symmetric bounds NOT assumed. | ✓ |
| F1 + sigma | More compact. 1-sigma standard error from bootstrap. User computes 95% via ±1.96σ. Loses asymmetry information. | |
| F1 + ci_lower + ci_upper + sigma + n_bootstrap | Maximalist. Schema bloat without obvious consumer. | |

**User's choice:** F1 + ci_lower + ci_upper (95%)
**Rationale captured in D-07:** Matches ROADMAP DIST-03 explicit phrasing; symmetric bounds not assumed (block-bootstrap distributions can be skewed for binary-classification F1 near boundary).

### Q4: 1km block boundary handling at MGRS tile edges

| Option | Description | Selected |
|--------|-------------|----------|
| Drop partial blocks | Bootstrap pool = full 1km blocks only; partial edge blocks dropped. Standard spatial-bootstrap practice. n_blocks_kept + n_blocks_dropped reported. | ✓ |
| Include partial blocks with proportional weight | Weighted-resampling. Preserves all data; adds complexity. | |
| Pad tile to nearest 1km — NaN-filled blocks | Reframe as 110×110 = 12100 blocks; out-of-tile pixels NaN. Same statistically; mechanically more complex. | |

**User's choice:** Drop partial blocks
**Rationale captured in D-08:** Standard spatial-bootstrap (Hall 1985 / Lahiri 2003); transparent; defensible; ~3.7% information loss bounded; n_blocks_kept + n_blocks_dropped disclosed in metrics.json.

---

## EU events orchestration + chained retry (DIST-06, DIST-07)

### Q1: EU 3-event matrix cell shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single aggregate cell, per-event sub-results | dist:eu cell renders as 'X/3 PASS' aggregate. metrics.json has per_event list + top-level aggregates. Phase 2 RTC-EU pattern. Single CONCLUSIONS narrative. Manifest unchanged. | ✓ |
| Three independent cells | dist:eu-aveiro, dist:eu-evros, dist:eu-romania as separate manifest entries; matrix grows from 10 to 12 cells. Clutters REL-01's '5×2 = 10 cells' commitment. | |
| Single cell with worst-event-wins semantics | Simpler matrix; loses per-event attribution. | |

**User's choice:** Single aggregate cell, per-event sub-results
**Rationale captured in D-10:** Phase 2 RTC-EU pattern; preserves REL-01 '5×2 = 10 cells' structural commitment; manifest unchanged.

### Q2: Existing v1.0 EU scripts disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Merge into declarative AOIS list | Single run_eval_dist_eu.py with EVENTS list looping sequentially with per-event try/except isolation (Phase 2 D-05/D-06). Both existing scripts migrate; nov15 stage becomes chained-retry sub-stage. Consistent with v1.1 conventions. | ✓ |
| Keep 3 separate scripts | run_eval_dist_eu_aveiro.py + run_eval_dist_eu_evros.py + run_eval_dist_eu_romania.py. More code. | |
| Rewrite from scratch — v1.0 scripts archive | Cleanest break; loses cached SAFE/IFG provenance unless plan-phase migrates cache directories. | |

**User's choice:** Merge into declarative AOIS list
**Rationale captured in D-11:** Phase 2 D-05/D-06 pattern; preserves v1.0 cache by migrating content; consistent retry/supervisor wrapping.

### Q3: Chained prior_dist_s1_product execution location

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded post-stage in Aveiro event | run_eval_dist_eu.py's aveiro entry has final stage retrying chained workflow on cached Sep28+Oct10 outputs to produce Nov15 alert. Result lands as per_event[aveiro].chained_run sub-result. Single Makefile target. | ✓ |
| Standalone Makefile target eval-dist-chained-eu | Cleaner separation; adds Makefile target and harness wiring. | |
| Defer entirely to v2 | If Phase 1 _mp.py bundle didn't fix hang, document failure and file upstream. Skip differentiator. | |

**User's choice:** Embedded post-stage in Aveiro event
**Rationale captured in D-13:** Logically tied to un-chained baseline (same SAFEs + DEM + enumerate); single supervisor invocation; cache stays under aveiro.

### Q4: Chained retry pass criterion

| Option | Description | Selected |
|--------|-------------|----------|
| Structurally-valid 10-layer DIST-ALERT product | Pass = DistS1ProductDirectory loads + 10 layers + DIST-STATUS non-empty. No F1 comparison (alert-promotion legitimately differs from un-chained). | ✓ |
| F1 within ±0.05 of un-chained Aveiro baseline | Tighter; risks false-fail if alert-promotion logic legitimately changes the disturbance footprint. | |
| Runs without crashing | Loosest — catches macOS-fork-hang regression but doesn't validate output usefulness. | |

**User's choice:** Structurally-valid 10-layer DIST-ALERT product
**Rationale captured in D-14:** Middle ground; catches dist-s1 hangs / partial outputs; doesn't false-fail on legitimate alert-promotion footprint divergence; aligns with DIST-07 'success reported as DIFFERENTIATOR'.

---

## CMR supersede + EFFIS rasterisation (DIST-04, DIST-05, P4.4)

### Q1: CMR probe wiring location

| Option | Description | Selected |
|--------|-------------|----------|
| Eval-time pre-stage in run_eval_dist.py | Stage 0 queries CMR; on hit fetches via earthaccess; on miss falls back to v0.1 CloudFront. Single decision point per eval. metrics.json reference_source: Literal[...]. | ✓ |
| Make-time pre-flight via supervisor | Supervisor probes before invoking; sets env var. Catches publication earlier; complicates supervisor; two decision points. | |
| Both — supervisor warns, eval-time decides | Banner + redundant CMR queries. | |

**User's choice:** Eval-time pre-stage in run_eval_dist.py
**Rationale captured in D-15:** Single decision point per eval; eliminates make-time/eval-time desync risk; harness already supports both Earthdata + CloudFront paths.

### Q2: Supersede semantics when operational publishes

| Option | Description | Selected |
|--------|-------------|----------|
| Replace metrics.json (v0.1 archived) | metrics.json overwritten with operational numbers; v0.1 moves to eval-dist/archive/v0.1_metrics_TIMESTAMP.json. CONCLUSIONS gets new sub-section; v0.1 preserved as 'pre-operational baseline'. Auditable via git + file timestamps. | ✓ |
| Render both side-by-side in metrics.json | reference_v0.1 + reference_operational blocks; matrix renders operational. Schema bloat after first publication week. | |
| Drop v0.1 entirely | Once operational detected, v0.1 removed. Loses pre-operational vs operational comparison datapoint. Not auditable after fact. | |

**User's choice:** Replace metrics.json (v0.1 archived)
**Rationale captured in D-16:** ROADMAP DIST-04 'no manual intervention'; auditable via git + timestamps; v0.1 archive remains readable for cross-version studies; long-term operational is single truth.

### Q3: EFFIS rasterisation default

| Option | Description | Selected |
|--------|-------------|----------|
| all_touched=False as default + report delta | Conservative; doesn't inflate recall via boundary pixels. Eval also computes all_touched=True as diagnostic. Primary F1 + all_touched_delta_f1 sub-field. | ✓ |
| all_touched=True as default + report delta | Inflates recall; catches boundary-overlap fires; closer to EFFIS's 10-20m polygon delineation intent. | |
| Both reported; matrix cell shows worse F1 | Strictest — prevents 'pick the rasterisation that flatters the metric'. Doubles compute (negligible). | |

**User's choice:** all_touched=False as default + report delta
**Rationale captured in D-17:** PITFALLS P4.4 mitigation; conservative; non-inflating; delta narrated in CONCLUSIONS + docs/validation_methodology.md §4.

### Q4: EFFIS WFS download retry policy

| Option | Description | Selected |
|--------|-------------|----------|
| owslib via harness with new EFFIS retry policy | Add 'effis' branch to harness.RETRY_POLICY (mirrors CDSE/Earthdata/CloudFront). WFS GetFeature wrapped in download_reference_with_retry. Phase 1 D-Claude's-Discretion harness consistency. Plan-phase commits endpoint URL + layer name (schema unverified). | ✓ |
| Direct owslib calls in eval script | Skip harness wiring; loses Phase 1 retry-policy discipline. | |
| Pre-cached GeoJSON committed to repo | Plan-phase manually downloads once; commits .geojson files. Reproducible; loses live cross-validation fidelity. | |

**User's choice:** owslib via harness with new EFFIS retry policy
**Rationale captured in D-18:** Phase 1 ENV-06 retry-policy pattern (5th source after CDSE/Earthdata/CloudFront/EGMS); plan-phase commits exact endpoint + layer name from probe.

---

## Claude's Discretion

The following items were noted as plan-phase decisions during the discussion (deferred to plan-phase per the captured CONTEXT.md "Claude's Discretion" subsection):

- Config-drift extraction code module location (extend compare_dist.py vs new validation/config_drift.py)
- Per-key delta table Pydantic schema in ConfigDriftReport
- EXPECTED_WALL_S actual values (estimates: ~3 hours N.Am., 6-10 hours EU)
- EFFIS WFS endpoint URL + layer name (research notes "schema unverified for 2026")
- owslib install location (pip layer vs conda-forge)
- Aveiro / Evros / Romania exact AOIs + dates with citations
- Chained-retry stage skip-condition (macOS-only vs everywhere)
- numpy.random.default_rng(seed) vs RandomState(seed) for bootstrap determinism
- Investigation-trigger entries in criteria.py for F1 CI width
- CONCLUSIONS_DIST_N_AM.md v1.0 baseline preamble framing details
- CMR query temporal window (±days tolerance around 2025-01-21)
- DIST cell_status Literal extension for 'DEFERRED' (additive change to matrix_schema.py)
- run_eval_dist.py Park Fire migration approach

## Deferred Ideas

The following came up during discussion as adjacent or future-milestone items, not Phase 5 deliverables:

- Operational monitoring chain with provisional→confirmed alert promotion (DIST-V2-01)
- Upstream PR for post_date_buffer_days default change in dist-s1 (DIST-V2-02)
- Full OPERA product-spec metadata validation through DistS1ProductDirectory (DIST-V2-03)
- Re-running against operational OPERA DIST-S1 as a planned activity (DIST-V2-04 — handled by auto-supersede if it lands mid-milestone)
- Promotion of extract_v01_config_drift to a generic validation/drift_gates.py module
- block_bootstrap_ci reuse for non-F1 metrics in Phase 6 DSWx
- EFFIS class-definition reconciliation (PITFALLS P4.5 narrative caveat in §4.3 only)
- Romania 2022 EU event substitution (plan-phase confirms event choice; EFFIS may not cover clear-cuts per PITFALLS P4.5)
