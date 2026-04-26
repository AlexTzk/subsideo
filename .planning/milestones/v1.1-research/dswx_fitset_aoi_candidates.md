# DSWx-S2 EU Fit-set AOI Candidates — Probe Report

**Probed:** 2026-04-26T20:55:58Z
**Source query:** RESEARCH.md pre-computed values (CDSE STAC network unavailable in execution environment; JRC tile downloads not executed to avoid timeout).
**Phase:** 6 (DSWx-S2 N.Am. + EU Recalibration)
**Decision:** D-01 (probe artifact) + D-02 (hybrid auto-reject + advisory pre-screen) + D-03 (P5.4 strict 1.2 ratio).
**Note:** Live CDSE STAC query for SENTINEL-2 collection returned empty (collection name mismatch — catalogue.dataspace.copernicus.eu/stac has no SENTINEL-2 collection in current API version). JRC tile downloads not attempted to avoid timeout. Fallback path per CONTEXT D-01: artifact ships with RESEARCH-table values.

## Biome Coverage

| # | biome | aoi | bbox (W,S,E,N) | mgrs_tile | jrc_unknown_pct | wet_dry_ratio | cloud_free_2021 | failure_mode_flags | recommended |
|---|-------|-----|----------------|-----------|-----------------|---------------|-----------------|---------------------|-------------|
| 1 | Mediterranean reservoir | Embalse de Alcántara (ES) | -7.05, 39.55, -6.65, 39.95 | 29SQE | 3.0% | 2.500 | 8 | clean | YES |
| 2 | Atlantic estuary | Tagus estuary (PT) | -9.45, 38.55, -8.85, 39.05 | 29SMC | 6.0% | 1.900 | 9 | tidal_turbidity: suspended sediment; advisory | YES |
| 3 | Boreal lake | Vänern (SE) | 12.40, 58.45, 14.20, 59.45 | 33VVF | 2.0% | 1.400 | 10 | glacier_or_frozen_lake: frozen surface; auto-reject (months [12, 1, 2]) | YES |
| 4 | Alpine valley | Lago di Garda (IT) | 10.55, 45.55, 10.85, 45.85 | 32TQR | 5.0% | 1.300 | 6 | mountain_shadow: low sun angle; advisory (months [10, 11, 12, 1, 2]) | YES |
| 5 | Iberian summer-dry | Doñana wetlands (ES) | -6.55, 36.80, -6.30, 37.05 | 29SQB | 7.0% | 2.100 | 7 | drought_year_risk: wetlands dry; alternate-year retry (years [2017, 2022]) | YES |
| 6 | Pannonian plain | Balaton (HU) — HELD OUT | 17.20, 46.60, 18.20, 46.95 | 33TXP | 3.0% | 1.500 | 8 | clean | HELD-OUT (test set) |

## N.Am. positive-control candidates (CONTEXT D-18 — runtime auto-pick)

| aoi | bbox (W,S,E,N) | mgrs_tile | epsg | jrc_year | jrc_month | citation |
|-----|----------------|-----------|------|----------|-----------|----------|
| Lake Tahoe (CA) | -120.20, 38.91, -119.90, 39.27 | 10SFH | 32610 | 2021 | 7 | USGS ScienceBase 2021 Sentinel-2 mosaic verified; T10SFH confirmed via RESEARCH lines 258-265 |
| Lake Pontchartrain (LA) | -90.45, 30.02, -89.62, 30.34 | 15RYP | 32615 | 2021 | 7 | python-mgrs centroid (30.18°N, -90.10°W) per RESEARCH lines 267-274; verify via live STAC in Plan 06-05 |

Note on Tahoe MGRS: T10SFH verified from USGS ScienceBase 2021 Sentinel-2 mosaic per RESEARCH §N.Am. MGRS tile resolution lines 258-265.
Note on Pontchartrain MGRS: T15RYP from python-mgrs centroid. CONTEXT D-18 lists 15RYR or 15RZR as alternatives — Plan 06-05 live STAC query will confirm.

## All Candidates Scored (18 EU + 2 N.Am.)

| aoi_id | biome | cloud_free_2021 | wet_dry_ratio | jrc_unknown_pct | auto_reject |
|--------|-------|-----------------|---------------|-----------------|-------------|
| alcantara | Mediterranean reservoir | 8 | 2.500 | 3.0% | no |
| bracciano | Mediterranean reservoir | 7 | 1.050 | 4.0% | YES (wet_dry_ratio=1.05 < 1.2) |
| buendia | Mediterranean reservoir | 6 | 1.800 | 5.0% | no |
| tagus | Atlantic estuary | 9 | 1.900 | 6.0% | no |
| loire | Atlantic estuary | 6 | 1.500 | 12.0% | no |
| severn | Atlantic estuary | 5 | 3.200 | 18.0% | no (advisory elevated) |
| vanern | Boreal lake | 10 | 1.400 | 2.0% | no |
| saimaa | Boreal lake | 4 | 1.150 | 8.0% | YES (wet_dry_ratio=1.15 < 1.2) |
| malaren | Boreal lake | 7 | 1.200 | 3.0% | no (marginal; 1.200 == threshold) |
| garda | Alpine valley | 6 | 1.300 | 5.0% | no |
| leman | Alpine valley | 5 | 1.250 | 4.0% | no |
| maggiore | Alpine valley | 5 | 1.280 | 6.0% | no |
| alarcon | Iberian summer-dry | 7 | 1.100 | 4.0% | YES (wet_dry_ratio=1.1 < 1.2) |
| albufera | Iberian summer-dry | 8 | 1.150 | 9.0% | YES (wet_dry_ratio=1.15 < 1.2) |
| donana | Iberian summer-dry | 7 | 2.100 | 7.0% | no |
| balaton | Pannonian plain | 8 | 1.500 | 3.0% | no (held-out) |
| tahoe | N.Am. positive control | 12 | 1.300 | 2.0% | N/A (N.Am.) |
| pontchartrain | N.Am. positive control | 10 | 1.400 | 4.0% | N/A (N.Am.) |

## Rejected candidates

Candidates auto-rejected by D-02 + D-03 hard signals (wet_dry_ratio < 1.2 OR jrc_unknown_pct > 20% OR cloud_free < 3):
- **Lago di Bracciano (IT)**: wet_dry_ratio=1.05 < 1.2 (volcanic crater lake; small storage variation below threshold)
- **Saimaa (FI)**: wet_dry_ratio=1.15 < 1.2 (frozen 6 months/year + fragmented geometry)
- **Embalse de Alarcón (ES)**: wet_dry_ratio=1.1 < 1.2 (drought year 2021; D-03 alternate-year retry path)
- **Albufera de Valencia (ES)**: wet_dry_ratio=1.15 < 1.2 (rice-paddy seasonal flooding not cleanly captured by JRC)

Advisory rejections (soft signals elevated in selection rationale — not hard auto-rejects):
- **Severn estuary (UK)**: 14m tidal range creates methodological ambiguity (ratio may be artificially inflated by mudflat exposure between scenes); advisory elevated to selection-level rejection
- **Loire estuary (FR)**: secondary to Tagus for Atlantic estuary biome; additional tidal-flat ambiguity beyond turbidity
- **Lac Léman (CH/FR)**: secondary to Garda; multi-national UTM zone boundary complicates tile alignment
- **Lago Maggiore (IT/CH)**: secondary to Garda; steeper north-end mountain shadows more severe
- **Mälaren (SE)**: secondary to Vänern; Stockholm urban drainage proximity
- **Embalse de Buendía (ES)**: secondary to Alcántara; smaller + narrower seasonality

## Selection Rationale

| Biome | Selected AOI | Why | Rejected alternatives |
|-------|-------------|-----|----------------------|
| Mediterranean reservoir | **Embalse de Alcántara (ES)** | Largest EU reservoir; wet/dry=2.5; strong signal; alternate years (2018 wet, 2017/2022 dry) | Bracciano: wet/dry < 1.2; Buendía: smaller + narrower seasonality |
| Atlantic estuary | **Tagus estuary (PT)** | wet/dry=1.9; honest stress test (turbidity = JRC commission/omission test per P5.2) | Loire: extra tidal-flat ambiguity; Severn: methodologically ambiguous (14m range) |
| Boreal lake | **Vänern (SE)** | Largest EU lake (5,650 km²); wet/dry=1.4; robust JRC reference; frozen-month auto-reject Dec-Feb applied | Saimaa: wet/dry < 1.2 + fragmented; Mälaren: urban drainage proximity |
| Alpine valley | **Lago di Garda (IT)** | Largest Italian Alpine lake (370 km²); wet/dry=1.3; deep clear water; mountain-shadow advisory = honest failure-mode test per P5.2 | Léman: UTM zone boundary; Maggiore: steeper shadows |
| Iberian summer-dry | **Doñana wetlands (ES)** | wet/dry=2.1 (often >2.0 per literature); shallow marismas; signal-rich | Alarcón: drought 2021 (wet/dry < 1.2); Albufera: class-3 ambiguity |
| Pannonian plain | **Balaton (HU) — HELD OUT** | v1.0 baseline (F1=0.7957); continuity; held-out discipline per BOOTSTRAP §5.4 | — |

## Decision

5 fit-set AOIs locked + Balaton held-out per CONTEXT D-01 + DSWX-03. Plan 06-06 fit-set compute commits against this list.

**Fit-set AOIs (input to `scripts/recalibrate_dswe_thresholds.py`):**
1. Embalse de Alcántara (ES) — bbox (-7.05, 39.55, -6.65, 39.95), MGRS 29SQE, EPSG 32629
2. Tagus estuary (PT) — bbox (-9.45, 38.55, -8.85, 39.05), MGRS 29SMC, EPSG 32629
3. Vänern (SE) — bbox (12.40, 58.45, 14.20, 59.45), MGRS 33VVF, EPSG 32633
4. Lago di Garda (IT) — bbox (10.55, 45.55, 10.85, 45.85), MGRS 32TQR, EPSG 32632
5. Doñana wetlands (ES) — bbox (-6.55, 36.80, -6.30, 37.05), MGRS 29SQB, EPSG 32629

**Held-out (gate-of-truth per BOOTSTRAP §5.4):**
- Balaton (HU) — bbox (17.20, 46.60, 18.20, 46.95), MGRS 33TXP, EPSG 32633
