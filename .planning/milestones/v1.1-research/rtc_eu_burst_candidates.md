# RTC-S1 EU Burst Candidates -- Probe Report

**Probed:** 2026-04-23T15:40:02Z
**Source query:** `asf_search` + `earthaccess` against ASF DAAC.
**Phase:** 2 (RTC-S1 EU Validation)
**Decision:** D-01 (probe artifact) + D-03 (5-regime fixed list) + D-04 (Claude drafts; user reviews).

## Regime Coverage

| # | regime | label | centroid_lat | expected_max_relief_m | opera_rtc_granules_2024_2025 | best_match_sensing_utc | best_match_granule | cached_safe | burst_id (fill-in) |
|---|--------|-------|--------------|-----------------------|------------------------------|------------------------|--------------------|-------------|---------------------|
| 1 | Alpine | Swiss/Italian Alps (Valtellina region) | 46.35 | ~3200 | 2907 | 2024-05-02T05:35:20Z | `S1A_IW_SLC__1SDV_20240502T053520_20240502T053547_053688_06856B_100B-SLC` | (none) | (derive via opera_utils.get_burst_id on the chosen granule) |
| 2 | Scandinavian | Northern Sweden (Norrbotten, >67°N) | 67.15 | ~500 | 5691 | (no SLC found) | (no SLC found) | (none) | (derive via opera_utils.get_burst_id on the chosen granule) |
| 3 | Iberian | Iberian Meseta (north of Madrid) | 41.15 | ~500 | 3022 | 2024-05-08T06:26:23Z | `S1A_IW_SLC__1SDV_20240508T062623_20240508T062650_053776_0688DB_1DAE-SLC` | (none) | (derive via opera_utils.get_burst_id on the chosen granule) |
| 4 | TemperateFlat | Po plain (Bologna, Italy) | 44.50 | ~100 | 2645 | 2024-05-05T17:06:33Z | `S1A_IW_SLC__1SDV_20240505T170633_20240505T170700_053739_068777_8386-SLC` | (not cached: eval-disp-egms/input) | (derive via opera_utils.get_burst_id on the chosen granule) |
| 5 | Fire | Central Portugal (Aveiro/Viseu fire footprint) | 40.70 | ~400 | 2709 | (no SLC found) | (no SLC found) | (not cached: eval-dist-eu/input) | (derive via opera_utils.get_burst_id on the chosen granule) |

## RTC-01 Mandatory Constraints Audit

- **>1000 m relief:** row #1 (Alpine, expected ~3200 m) -- PASS candidate.
- **>55°N:** row #2 (Scandinavian, centroid ~67.15°N) -- PASS candidate.

Claude has drafted the five regime rows per BOOTSTRAP §1.1 + CONTEXT D-03. User review per D-04 resolves:

1. Which granule from `best_match_granule` is the target SLC for each fresh burst (Alpine / Scandinavian / Iberian).
2. The concrete `burst_id` (JPL lowercase `t<relorb>_<burst>_iw<swath>`) derived from the chosen granule. This can be computed via `opera_utils.burst_frame_db.get_burst_id_geojson()` + visual inspection, or by running a Python snippet using `opera_utils.get_burst_id` over the SAFE.
3. Whether any regime should be swapped (opera_rtc_granules_2024_2025 == 0 makes that candidate unusable).
4. Sensing UTC hour to pass to `select_opera_frame_by_utc_hour` (harness default: +-1h tolerance).

Plan 02-04 locks the 5-burst final list from this artifact. Downstream the probe doc is referenced (via `see probe artifact`) but not re-run at eval time.

## Plan 02-05 Task 1 Follow-up -- Burst IDs Derived from OPERA L2 RTC Catalog (2026-04-23)

User approved Task 1 checkpoint with signal `lgtm-proceed-after-probe`. Probe was re-run
and populated `opera_rtc_granules_2024_2025` counts (all >0 -> all 5 regimes usable).

Because the probe's SLC query used a narrow 2024 summer window + expected relorb filter,
2 regimes (Scandinavian, Fire) returned "(no SLC found)" for `best_match_granule`. The
probe's 2024-2025 OPERA count nonetheless shows all 5 regimes have thousands of OPERA
RTC granules available. Concrete burst_ids were derived downstream via
`scripts/derive_burst_ids_from_opera.py` which queries `earthaccess.search_data(short_name=
"OPERA_L2_RTC-S1_V1", bounding_box=regime_bbox)` over 2024-05..10 and extracts the
dominant burst_id (via `opera_utils.get_burst_id`) from OPERA RTC granule names.

| # | regime | burst_id (OPERA-dominant) | rel_orb | subswath | sensing_utc | track notes |
|---|--------|---------------------------|---------|----------|-------------|-------------|
| 1 | Alpine | `t066_140413_iw1` | 66 | IW1 | 2024-05-02T05:35:47Z | matches probe draft (track 66 ascending over Valtellina) |
| 2 | Scandinavian | `t058_122828_iw3` | 58 | IW3 | 2024-05-01T16:07:25Z | OPERA coverage heavier on track 58 than draft track 29 |
| 3 | Iberian | `t103_219329_iw1` | 103 | IW1 | 2024-05-04T18:03:39Z | OPERA coverage heavier on track 103 than draft track 154 |
| 4 | TemperateFlat | `t117_249422_iw2` | 117 | IW2 | 2021-03-14T17:05:00Z | unchanged from probe draft (Bologna pattern from Phase 1 DISP-EGMS) |
| 5 | Fire | `t045_094744_iw3` | 45 | IW3 | 2024-05-12T18:36:21Z | OPERA coverage heavier on track 45 than draft track 154 |

**UTM zones unchanged**: output_epsg values in `BURSTS` are longitude-derived (UTM 29N-34N
across the 5 regimes), so the track reassignments above do not change the UTM stamp.

**RTC-01 mandatory constraints still satisfied**:
- `>1000 m relief`: Row 1 Alpine (expected ~3200 m) -- unchanged.
- `>55°N`: Row 2 Scandinavian (centroid 67.15°N) -- unchanged.

Locked into `run_eval_rtc_eu.py::BURSTS` on 2026-04-23 (this Task 1 follow-up commit).

## Query reproducibility

Probe: `micromamba run -n subsideo python scripts/probe_rtc_eu_candidates.py`.
Burst-id derivation: `micromamba run -n subsideo python scripts/derive_burst_ids_from_opera.py`.

Requires `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD` in env or `.env`. Counts reflect ASF catalog state at probe time; a re-run may show different numbers as OPERA operational products publish.
