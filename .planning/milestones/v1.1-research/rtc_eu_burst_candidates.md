# RTC-S1 EU Burst Candidates -- Probe Report

**Probed:** (initial draft -- probe not yet executed)
**Source query:** `asf_search` + `earthaccess` against ASF DAAC (run `scripts/probe_rtc_eu_candidates.py` to populate live counts).
**Phase:** 2 (RTC-S1 EU Validation)
**Decision:** D-01 (probe artifact) + D-03 (5-regime fixed list) + D-04 (Claude drafts; user reviews).

## Regime Coverage (Claude-drafted; requires user review per D-04)

| # | regime | label | centroid_lat | expected_max_relief_m | opera_rtc_granules_2024_2025 | best_match_sensing_utc | best_match_granule | cached_safe | burst_id (fill-in) |
|---|--------|-------|--------------|-----------------------|------------------------------|------------------------|--------------------|-------------|---------------------|
| 1 | Alpine | Swiss/Italian Alps (Valtellina region) | 46.35 | ~3200 | TBD (run probe) | TBD | TBD | (none) | (derive via opera_utils.get_burst_id on the chosen granule) |
| 2 | Scandinavian | Northern Sweden (Norrbotten, >67°N) | 67.15 | ~500 | TBD (run probe) | TBD | TBD | (none) | (derive via opera_utils.get_burst_id on the chosen granule) |
| 3 | Iberian | Iberian Meseta (north of Madrid) | 41.15 | ~500 | TBD (run probe) | TBD | TBD | (none) | (derive via opera_utils.get_burst_id on the chosen granule) |
| 4 | TemperateFlat | Po plain (Bologna, Italy) | 44.50 | ~100 | TBD (run probe) | TBD | TBD | `eval-disp-egms/input/` (Phase 1 DISP-EGMS) | `t117_249422_iw2` (Bologna pattern; verify via probe) |
| 5 | Fire | Central Portugal (Aveiro/Viseu fire footprint) | 40.70 | ~400 | TBD (run probe) | TBD | TBD | `eval-dist-eu/input/` (v1.0 DIST-EU) | (derive via opera_utils.get_burst_id from DIST-EU cached SAFE) |

## RTC-01 Mandatory Constraints Audit

- **>1000 m relief:** row #1 (Alpine, expected ~3200 m) -- PASS candidate.
- **>55°N:** row #2 (Scandinavian, centroid ~67.15°N) -- PASS candidate.

Both RTC-01 constraints are satisfied by the two fresh-download bursts (Alpine + Scandinavian). The three remaining regimes (Iberian / TemperateFlat / Fire) broaden coverage without imposing the constraints.

Claude has drafted the five regime rows per BOOTSTRAP §1.1 + CONTEXT D-03. User review per D-04 resolves:

1. Run `scripts/probe_rtc_eu_candidates.py` to populate `opera_rtc_granules_2024_2025`, `best_match_sensing_utc`, `best_match_granule` columns.
2. For each fresh-download regime (rows 1-3), derive the concrete `burst_id` (JPL lowercase `t<relorb>_<burst>_iw<swath>`) from the chosen granule -- inspect the SAFE with `opera_utils.get_burst_id` or via `s1reader.load_bursts` metadata.
3. For cached regimes (rows 4-5), inspect the existing `eval-disp-egms/input/` and `eval-dist-eu/input/` directories; if no SAFE is cached yet (Phase 1 may not have populated them), treat those regimes as fresh-download too.
4. Confirm sensing UTC hour to pass to `select_opera_frame_by_utc_hour` (default ±1h).
5. If any regime shows `opera_rtc_granules_2024_2025 == 0`, swap it for a documented-stable fallback and update this table.

## Candidate Rationale (BOOTSTRAP §1.1 + P1.1 prevention)

- **Row 1 -- Alpine (Valtellina / Swiss-Italian Alps):** satisfies RTC-01 ">1000 m relief" mandatory constraint. Valtellina spans ~800 m (valley floor) to ~3500 m (Disgrazia / Bernina ridges); expected_max_relief_m ~3200 m puts this comfortably above the 1000 m bar. Tests steep-terrain DEM / layover / shadow handling that flat-terrain regimes cannot surface (PITFALLS P1.1). Fresh download; relorb 66 is the closest regular Sentinel-1 ascending track over the Western Alps.
- **Row 2 -- Scandinavian (Northern Sweden, Norrbotten):** satisfies RTC-01 ">55°N" mandatory constraint with large headroom (67.15°N is ~12° above the bar). Exercises high-latitude GLO-30 grid-spacing artefacts (cells get narrower in lat/lon further north) that mid-latitude regimes never touch; also validates POEORB/RESORB handling where Sentinel-1 revisit frequency increases toward the pole. Fresh download; relorb 29 hits Norrbotten on ascending passes.
- **Row 3 -- Iberian arid (Meseta north of Madrid):** broadens terrain diversity into a low-coherence arid backdrop consistent with the Phase 3 CSLC Iberian AOI family. Dry soil moisture regime stresses RTC radiometric calibration differently from the humid northern Europe cases. Fresh download; relorb 154 is the standard Iberian descending track.
- **Row 4 -- TemperateFlat (Po plain, Bologna):** "free burst" -- the Bologna AOI is cached from Phase 1's DISP-EGMS eval at `eval-disp-egms/input/`, so the D-02 harness search-path fallback reuses that SAFE with zero extra download cost. The burst_id `t117_249422_iw2` is the Bologna burst already proven by DISP-EGMS cell; verify via probe. Temperate-flat terrain anchors the baseline at minimum complexity.
- **Row 5 -- Fire (Aveiro/Viseu, Central Portugal):** "free burst" -- cached from Phase 1's DIST-EU eval at `eval-dist-eu/input/`. The 2024 Aveiro/Viseu fire footprint exercises RTC over a region with known surface-property change (scorched vegetation, exposed soil) -- reference-agreement should still pass because RTC is geometric + radiometric, not land-cover-dependent; any material RMSE drift between subsideo and OPERA here would flag a calibration issue reacting to low-coherence surfaces.

**P1.1 cached-bias prevention check:** 3 of 5 bursts (rows 1-3) are fresh downloads; both RTC-01-mandatory-constraint-satisfying bursts (Alpine + Scandinavian) are fresh. The cheapness bias PITFALLS P1.1 warns about is structurally excluded: dropping either Alpine or Scandinavian would break the mandatory constraints, so budget pressure cannot silently narrow the claim.

## Next Step

Plan 02-04 locks the 5-burst final list from this artifact into `run_eval_rtc_eu.py::BURSTS`. The probe artifact is the source of truth; re-running the probe overwrites it.

## Query reproducibility

Re-run: `micromamba run -n subsideo python scripts/probe_rtc_eu_candidates.py`.

Requires `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD` in env or `.env`.
