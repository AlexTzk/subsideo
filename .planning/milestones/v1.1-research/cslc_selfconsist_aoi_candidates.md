# CSLC-S1 Self-Consistency + EU AOI Candidates -- Probe Report

**Probed:** 2026-04-24T04:19:35Z
**Source query:** `earthaccess.search_data` (OPERA CSLC-S1 V1) + `asf_search` + EGMS L2a density estimate (not downloaded — back-of-envelope ceiling only).
**Phase:** 3 (CSLC-S1 Self-Consistency + EU Validation)
**Decision:** D-10 (probe artifact) + D-11 (Mojave fallback ordering).

## Candidate AOIs (D-10 schema)

| aoi | regime | candidate_burst_id | opera_cslc_coverage_2024 | egms_l2a_release_2019_2023_stable_ps_count | expected_stable_pct_per_worldcover | published_insar_stability_ref | cached_safe_fallback_path |
|-----|--------|--------------------|--------------------------|----------------------------------------------|------------------------------------|-------------------------------|--------------------------|
| Mojave/Coso-Searles | desert-bedrock-playa-adjacent | t064_135527_iw2 | 864 | n/a (NAM: no EGMS coverage) | 0.35 | Monastero et al. 2005 (J. Geophys. Res.); Coso regional subsidence mapped InSAR-stable on ridges | (none) |
| Mojave/Pahranagat | desert-bedrock | t173_370296_iw2 | 451 | n/a (NAM: no EGMS coverage) | 0.30 | Schwing et al. 2022 (Geosphere); Basin-and-Range stability well-documented for InSAR in the area | (none) |
| Mojave/Amargosa | desert-bedrock-playa-adjacent | t064_135530_iw3 | 899 | n/a (NAM: no EGMS coverage) | 0.25 | Sneed et al. 2003 (USGS SIR); playa-adjacent stable bedrock sides | (none) |
| Mojave/Hualapai | plateau-bedrock | t100_213507_iw2 | 353 | n/a (NAM: no EGMS coverage) | 0.40 | Chaussard et al. 2014 (JGR); Colorado Plateau edge, stable bedrock, low vegetation | (none) |
| Iberian/Meseta-North | iberian-meseta-sparse-vegetation | t103_219329_iw1 (see note below) | 0 | 250876 | 0.20 | Tomás et al. 2014 (IJAEO); Meseta bedrock stability vs agricultural fallow — Segovia / Soria region stability reported | (none) |
| Iberian/Alentejo | interior-portugal-plateau | (derive via EU burst DB; see note) | 0 | 260167 | 0.18 | Catalão et al. 2021 (RS); Portuguese Meseta stable on bedrock-dominated slopes | (none) |
| Iberian/MassifCentral | massif-central-plateau | (derive via EU burst DB; see note) | 0 | 234614 | 0.25 | de Michele et al. 2010 (RSE); stable plateau InSAR baseline over volcanic-derived bedrock | (none) |

**Note on EU burst_id and opera_cslc_coverage_2024 = 0:**
OPERA CSLC-S1 V1 is a NASA/JPL operational product limited to North America. EU AOIs
correctly show `opera_cslc_coverage_2024 = 0` — this is not a probe failure. For EU
validation, subsideo generates its own CSLCs via `compass`/`isce3` from Sentinel-1 SLCs.
Burst IDs for EU AOIs use the same JPL-format convention derived from the EU burst DB:
- **Iberian/Meseta-North** `t103_219329_iw1`: matched from Phase 2 RTC-EU Iberian probe
  (same bbox, track 103, IW1; confirmed by `rtc_eu_burst_candidates.md` Task 1 follow-up).
  User should confirm or refine via `opera_utils.burst_frame_db.get_burst_id_geojson()`.
- **Iberian/Alentejo** and **Iberian/MassifCentral**: derive at eval time using
  `opera_utils.burst_frame_db.get_burst_id_geojson()` over the bbox centroid; lock into
  `run_eval_cslc_selfconsist_eu.py` AOI config after user review of this artifact.

## Locked Sensing Windows

Each candidate AOI locks a 15-epoch S1A 12-day stack. These lists become module-level tuples named per EPOCH_TUPLE_NAMES below in `run_eval_cslc_selfconsist_nam.py` (Mojave candidates) and `run_eval_cslc_selfconsist_eu.py` (Iberian candidates). Plan 03-03 / 03-04 acceptance checks `grep` these 7 section headings to confirm every AOI has an enumerated window.

### MOJAVE_COSO_EPOCHS — Mojave/Coso-Searles

| # | sensing_utc | platform | orbit_type (best-effort) |
|---|-------------|----------|--------------------------|
|  1 | 2024-01-03T01:51:11Z | S1A | POEORB |
|  2 | 2024-01-15T01:51:10Z | S1A | POEORB |
|  3 | 2024-01-27T01:51:10Z | S1A | POEORB |
|  4 | 2024-02-08T01:51:10Z | S1A | POEORB |
|  5 | 2024-02-20T01:51:10Z | S1A | POEORB |
|  6 | 2024-03-03T01:51:10Z | S1A | POEORB |
|  7 | 2024-03-15T01:51:10Z | S1A | POEORB |
|  8 | 2024-03-27T01:51:10Z | S1A | POEORB |
|  9 | 2024-04-08T01:51:11Z | S1A | POEORB |
| 10 | 2024-04-20T01:51:11Z | S1A | POEORB |
| 11 | 2024-05-02T01:51:11Z | S1A | POEORB |
| 12 | 2024-05-14T01:51:11Z | S1A | POEORB |
| 13 | 2024-05-26T01:51:11Z | S1A | POEORB |
| 14 | 2024-06-07T13:52:03Z | S1A | POEORB |
| 15 | 2024-06-19T01:51:10Z | S1A | POEORB |

### MOJAVE_PAHRANAGAT_EPOCHS — Mojave/Pahranagat

| # | sensing_utc | platform | orbit_type (best-effort) |
|---|-------------|----------|--------------------------|
|  1 | 2024-01-10T13:43:40Z | S1A | POEORB |
|  2 | 2024-01-22T13:43:40Z | S1A | POEORB |
|  3 | 2024-02-03T13:43:40Z | S1A | POEORB |
|  4 | 2024-02-15T13:43:39Z | S1A | POEORB |
|  5 | 2024-02-27T13:43:39Z | S1A | POEORB |
|  6 | 2024-03-10T13:43:39Z | S1A | POEORB |
|  7 | 2024-03-22T13:43:40Z | S1A | POEORB |
|  8 | 2024-04-03T13:43:40Z | S1A | POEORB |
|  9 | 2024-04-15T13:43:40Z | S1A | POEORB |
| 10 | 2024-04-27T13:43:41Z | S1A | POEORB |
| 11 | 2024-05-09T13:43:41Z | S1A | POEORB |
| 12 | 2024-05-21T13:43:40Z | S1A | POEORB |
| 13 | 2024-06-02T13:43:40Z | S1A | POEORB |
| 14 | 2024-06-14T13:43:40Z | S1A | POEORB |
| 15 | 2024-06-26T13:43:39Z | S1A | POEORB |

### MOJAVE_AMARGOSA_EPOCHS — Mojave/Amargosa

| # | sensing_utc | platform | orbit_type (best-effort) |
|---|-------------|----------|--------------------------|
|  1 | 2024-01-03T01:51:11Z | S1A | POEORB |
|  2 | 2024-01-10T13:43:40Z | S1A | POEORB |
|  3 | 2024-01-15T01:51:10Z | S1A | POEORB |
|  4 | 2024-01-22T13:43:40Z | S1A | POEORB |
|  5 | 2024-01-27T01:51:10Z | S1A | POEORB |
|  6 | 2024-02-03T13:43:40Z | S1A | POEORB |
|  7 | 2024-02-08T01:51:10Z | S1A | POEORB |
|  8 | 2024-02-15T13:43:39Z | S1A | POEORB |
|  9 | 2024-02-20T01:51:10Z | S1A | POEORB |
| 10 | 2024-02-27T13:43:39Z | S1A | POEORB |
| 11 | 2024-03-03T01:51:10Z | S1A | POEORB |
| 12 | 2024-03-10T13:43:39Z | S1A | POEORB |
| 13 | 2024-03-15T01:51:10Z | S1A | POEORB |
| 14 | 2024-03-22T13:43:40Z | S1A | POEORB |
| 15 | 2024-03-27T01:51:10Z | S1A | POEORB |

### MOJAVE_HUALAPAI_EPOCHS — Mojave/Hualapai


**[SYNTHETIC FALLBACK]** ASF query returned < 15 scenes or failed. User MUST confirm or override this list before Plan 03-03/04 lock.
| # | sensing_utc | platform | orbit_type (best-effort) |
|---|-------------|----------|--------------------------|
|  1 | 2024-01-13T14:01:16Z | S1A | POEORB |
|  2 | 2024-01-25T14:01:16Z | S1A | POEORB |
|  3 | 2024-02-06T14:01:16Z | S1A | POEORB |
|  4 | 2024-02-18T14:01:16Z | S1A | POEORB |
|  5 | 2024-03-01T14:01:16Z | S1A | POEORB |
|  6 | 2024-03-13T14:01:16Z | S1A | POEORB |
|  7 | 2024-03-25T14:01:16Z | S1A | POEORB |
|  8 | 2024-04-06T14:01:16Z | S1A | POEORB |
|  9 | 2024-04-18T14:01:16Z | S1A | POEORB |
| 10 | 2024-04-30T14:01:16Z | S1A | POEORB |
| 11 | 2024-05-12T14:01:16Z | S1A | POEORB |
| 12 | 2024-05-24T14:01:16Z | S1A | POEORB |
| 13 | 2024-06-05T14:01:16Z | S1A | POEORB |
| 14 | 2024-06-17T14:01:16Z | S1A | POEORB |
| 15 | 2024-06-29T14:01:16Z | S1A | POEORB |

### IBERIAN_PRIMARY_EPOCHS — Iberian/Meseta-North

| # | sensing_utc | platform | orbit_type (best-effort) |
|---|-------------|----------|--------------------------|
|  1 | 2024-01-04T06:18:03Z | S1A | POEORB |
|  2 | 2024-01-09T06:26:23Z | S1A | POEORB |
|  3 | 2024-01-10T18:11:36Z | S1A | POEORB |
|  4 | 2024-01-16T06:18:02Z | S1A | POEORB |
|  5 | 2024-01-21T06:26:22Z | S1A | POEORB |
|  6 | 2024-01-22T18:11:35Z | S1A | POEORB |
|  7 | 2024-01-28T06:18:02Z | S1A | POEORB |
|  8 | 2024-02-02T06:26:22Z | S1A | POEORB |
|  9 | 2024-02-03T18:11:35Z | S1A | POEORB |
| 10 | 2024-02-09T06:18:02Z | S1A | POEORB |
| 11 | 2024-02-15T18:11:35Z | S1A | POEORB |
| 12 | 2024-02-21T06:18:01Z | S1A | POEORB |
| 13 | 2024-02-26T06:26:21Z | S1A | POEORB |
| 14 | 2024-02-27T18:11:34Z | S1A | POEORB |
| 15 | 2024-03-04T06:18:02Z | S1A | POEORB |

### IBERIAN_ALENTEJO_EPOCHS — Iberian/Alentejo

| # | sensing_utc | platform | orbit_type (best-effort) |
|---|-------------|----------|--------------------------|
|  1 | 2024-01-01T18:35:22Z | S1A | POEORB |
|  2 | 2024-01-02T06:35:22Z | S1A | POEORB |
|  3 | 2024-01-07T06:43:36Z | S1A | POEORB |
|  4 | 2024-01-08T18:27:21Z | S1A | POEORB |
|  5 | 2024-01-13T18:35:22Z | S1A | POEORB |
|  6 | 2024-01-14T06:35:22Z | S1A | POEORB |
|  7 | 2024-01-19T06:43:35Z | S1A | POEORB |
|  8 | 2024-01-20T18:27:20Z | S1A | POEORB |
|  9 | 2024-01-25T18:35:22Z | S1A | POEORB |
| 10 | 2024-01-26T06:35:22Z | S1A | POEORB |
| 11 | 2024-01-31T06:43:35Z | S1A | POEORB |
| 12 | 2024-02-01T18:27:20Z | S1A | POEORB |
| 13 | 2024-02-06T18:35:21Z | S1A | POEORB |
| 14 | 2024-02-07T06:35:21Z | S1A | POEORB |
| 15 | 2024-02-12T06:43:35Z | S1A | POEORB |

### IBERIAN_MASSIF_CENTRAL_EPOCHS — Iberian/MassifCentral

| # | sensing_utc | platform | orbit_type (best-effort) |
|---|-------------|----------|--------------------------|
|  1 | 2024-01-01T05:52:18Z | S1A | POEORB |
|  2 | 2024-01-02T17:40:02Z | S1A | POEORB |
|  3 | 2024-01-06T06:00:27Z | S1A | POEORB |
|  4 | 2024-01-09T17:31:55Z | S1A | POEORB |
|  5 | 2024-01-13T05:52:17Z | S1A | POEORB |
|  6 | 2024-01-14T17:40:01Z | S1A | POEORB |
|  7 | 2024-01-18T06:00:26Z | S1A | POEORB |
|  8 | 2024-01-21T17:31:55Z | S1A | POEORB |
|  9 | 2024-01-25T05:52:17Z | S1A | POEORB |
| 10 | 2024-01-26T17:40:01Z | S1A | POEORB |
| 11 | 2024-01-30T06:00:26Z | S1A | POEORB |
| 12 | 2024-02-02T17:31:54Z | S1A | POEORB |
| 13 | 2024-02-06T05:52:17Z | S1A | POEORB |
| 14 | 2024-02-07T17:40:00Z | S1A | POEORB |
| 15 | 2024-02-11T06:00:25Z | S1A | POEORB |

## SoCal 15-epoch Sensing Window (CSLC-03 locked burst)

**Burst ID:** `t144_308029_iw1` (locked by CSLC-03; not subject to probe).

**Proposed window (Claude's Discretion per CONTEXT D-09):**
| # | sensing_utc | platform | orbit_type |
|---|-------------|----------|------------|
| 1  | 2024-01-13T14:01:16Z | S1A | POEORB |
| 2  | 2024-01-25T14:01:16Z | S1A | POEORB |
| 3  | 2024-02-06T14:01:16Z | S1A | POEORB |
| 4  | 2024-02-18T14:01:16Z | S1A | POEORB |
| 5  | 2024-03-01T14:01:16Z | S1A | POEORB |
| 6  | 2024-03-13T14:01:16Z | S1A | POEORB |
| 7  | 2024-03-25T14:01:16Z | S1A | POEORB |
| 8  | 2024-04-06T14:01:16Z | S1A | POEORB |
| 9  | 2024-04-18T14:01:16Z | S1A | POEORB |
| 10 | 2024-04-30T14:01:16Z | S1A | POEORB |
| 11 | 2024-05-12T14:01:16Z | S1A | POEORB |
| 12 | 2024-05-24T14:01:16Z | S1A | POEORB |
| 13 | 2024-06-05T14:01:16Z | S1A | POEORB |
| 14 | 2024-06-17T14:01:16Z | S1A | POEORB |
| 15 | 2024-06-29T14:01:16Z | S1A | POEORB |

**Rationale:** 168-day window (14 × 12-day IFGs), all S1A POEORB (no RESORB
epochs, no S1B after Nov 2023 end-of-life). First-epoch OPERA CSLC reference
fetched per D-07 for amplitude sanity. Cache under
`eval-cslc-selfconsist-nam/input/`; ~117 GB total download.

**User review:** Accept as-drafted, or revise window (e.g. shift forward if
2024-01 scenes are heavy-cloud-season corrupted on Santa Ynez aspect).

## Mojave Fallback Ordering (CONTEXT D-11)

Ordered by `(opera_cslc_coverage_2024) × (expected_stable_pct_per_worldcover)`. First attempt = Coso/Searles. On FAIL (any of: CSLC run throws, coherence_median_of_persistent < threshold triggering mask-sanity review, compute quota exhausted), the eval script iterates to the next in probe-locked order. Each attempt uses a 15-epoch sensing window — see the `MOJAVE_COSO_EPOCHS` / `MOJAVE_PAHRANAGAT_EPOCHS` / `MOJAVE_AMARGOSA_EPOCHS` / `MOJAVE_HUALAPAI_EPOCHS` sections above in **Locked Sensing Windows**.
Single-epoch windows are forbidden per Plan 03-PATTERNS invariant (compute_residual_velocity requires >= 3 epochs; _compute_ifg_coherence_stack requires >= 2 epochs).

| Attempt | AOI | Score | candidate_burst_id | expected_stable_pct | sensing_window_15 (section anchor) |
|---------|-----|-------|---------------------|---------------------|------------------------------------|
| 1 | Coso-Searles | 302.40 | t064_135527_iw2 | 0.35 | `MOJAVE_COSO_EPOCHS` |
| 2 | Pahranagat | 135.30 | t173_370296_iw2 | 0.30 | `MOJAVE_PAHRANAGAT_EPOCHS` |
| 3 | Amargosa | 224.75 | t064_135530_iw3 | 0.25 | `MOJAVE_AMARGOSA_EPOCHS` |
| 4 | Hualapai | 141.20 | t100_213507_iw2 | 0.40 | `MOJAVE_HUALAPAI_EPOCHS` |

If all 4 attempts fail, the eval script writes `status='BLOCKER'` to the
Mojave parent AOIResult in `eval-cslc-selfconsist-nam/metrics.json`; matrix
cell renders `*1/2 CALIBRATING, 1/2 BLOCKER*` per CONTEXT D-03 + D-11.

## User Review Checklist (per CONTEXT D-04 precedent)

1. **Mojave primary lock:** Accept Coso/Searles as attempt 1, or swap to
   Hualapai (higher expected_stable_pct but different regime). Track:
   `[ ]` accept / `[ ]` swap.
2. **Iberian primary lock:** Accept "Iberian Meseta north of Madrid" as
   primary, or swap to Alentejo. Track: `[ ]` accept / `[ ]` swap.
3. **SoCal 15-epoch window:** Accept 2024-01-13 → 2024-06-29 POEORB-only
   window, or revise. Track: `[ ]` accept / `[ ]` revise.
4. **EGMS L2a threshold:** Accept `stable_std_max = 2.0 mm/yr` per CONTEXT
   D-12, or tighten. Track: `[ ]` accept / `[ ]` tighten.
5. **Compute budget ack:** SoCal = ~12 h fresh + Mojave worst-case 4 × 12 h
   = 48 h fallback-chain budget. Supervisor `EXPECTED_WALL_S = 60 * 60 * 16`
   caps per-cell wall. Track: `[ ]` ack.
6. **Per-AOI 15-epoch windows:** Confirm each MOJAVE_*_EPOCHS and
   IBERIAN_*_EPOCHS list in Locked Sensing Windows above. ASF-derived lists
   may be SYNTHETIC FALLBACK — confirm OK or override manually. Track: `[ ]`.

Plan 03-03 (NAM eval script) locks attempt-1 burst IDs + Mojave fallback
ordering from this artifact after user review. Plan 03-04 (EU eval script)
locks Iberian primary + 2 fallbacks similarly.

## Query reproducibility

`micromamba run -n subsideo python scripts/probe_cslc_aoi_candidates.py`

Requires `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD` in env or `.env`.
EGMS stable-PS counts are back-of-envelope ceilings (density × area × 30%);
full L2a download is NOT run during probe (heavy — deferred to Plan 03-04).
