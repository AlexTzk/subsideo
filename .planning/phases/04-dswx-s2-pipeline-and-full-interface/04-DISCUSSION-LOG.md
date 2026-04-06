# Phase 4: DSWx-S2 Pipeline and Full Interface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 04-dswx-s2-pipeline-and-full-interface
**Areas discussed:** DSWx algorithm porting, JRC validation approach, CLI subcommand design, Validation report format

---

## DSWx Algorithm Porting

| Option | Description | Selected |
|--------|-------------|----------|
| OPERA defaults first | Start with OPERA DSWx-HLS DSWE thresholds translated to S2 band equivalents. Validate against JRC. Only invest in EU-specific tuning if defaults fail. | ✓ |
| EU-tuned from the start | Research EU-specific spectral thresholds using JRC as training data before building the pipeline. | |
| Configurable thresholds | Implement with all DSWE thresholds as config parameters. Users can tune for their AOI. | |

**User's choice:** OPERA defaults first
**Notes:** Ship with translated OPERA thresholds; EU tuning only if F1 < 0.90

| Option | Description | Selected |
|--------|-------------|----------|
| SCL band only | Use Sentinel-2 L2A's built-in Scene Classification Layer. Simple, no extra deps. | ✓ |
| s2cloudless + SCL | Supplement SCL with ML-based cloud detection. Better accuracy but adds dependency. | |
| You decide | Claude picks based on OPERA DSWx-HLS approach. | |

**User's choice:** SCL band only
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| 30m to match OPERA spec | Downsample to 30m UTM posting. Consistent with other products. JRC is also 30m. | ✓ |
| 10m native resolution | Keep S2's native 10m for maximum detail. Breaks OPERA format compliance. | |
| Both via config flag | Default 30m, optional --resolution 10 flag. | |

**User's choice:** 30m to match OPERA spec
**Notes:** None

---

## JRC Validation Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Monthly water history | JRC Monthly Water History maps. Match DSWx output month to JRC month. Most direct comparison. | ✓ |
| Yearly water occurrence | JRC Yearly Water Occurrence (0-100% frequency). Less precise but smooths seasonal variation. | |
| Water transitions map | JRC Water Transitions (permanent/seasonal/new/lost). Richer but more complex metrics. | |

**User's choice:** Monthly water history
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Direct HTTP download | Download JRC tiles from ec.europa.eu. No GEE dependency. Tile-based pattern. | ✓ |
| Google Earth Engine API | Use earthengine-api. More flexible but adds GEE dependency and auth. | |
| You decide | Claude picks simplest approach. | |

**User's choice:** Direct HTTP download
**Notes:** None

---

## CLI Subcommand Design

| Option | Description | Selected |
|--------|-------------|----------|
| GeoJSON file path | --aoi path/to/aoi.geojson. Simple, standard, works with any GIS tool output. | ✓ |
| File path or inline bbox | --aoi can be GeoJSON file OR bbox string. Auto-detect format. | |
| File path or WKT | --aoi accepts GeoJSON file or WKT string. | |

**User's choice:** GeoJSON file path
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Two separate flags | --start 2025-01-01 --end 2025-03-01. Explicit, ISO 8601. | ✓ |
| Single slash-separated | --date-range 2025-01-01/2025-03-01. OGC/STAC convention. | |
| You decide | Claude picks based on typer and pipeline signatures. | |

**User's choice:** Two separate flags
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Loguru structured logging | Stage-level log messages. --verbose for debug. No progress bars. | ✓ |
| Rich progress bars + logging | Typer's rich integration for progress bars. More visual but adds rich dep. | |
| You decide | Claude picks based on existing loguru setup. | |

**User's choice:** Loguru structured logging
**Notes:** None

---

## Validation Report Format

| Option | Description | Selected |
|--------|-------------|----------|
| Per-product reports | One report per product type. Simpler to generate and review. | ✓ |
| Combined summary report | Single report covering all validated products. More comprehensive. | |
| Both | Per-product reports AND combined summary. Most complete. | |

**User's choice:** Per-product reports
**Notes:** None

**Figure selection (multi-select):**

| Option | Description | Selected |
|--------|-------------|----------|
| Spatial difference map | Side-by-side or overlay showing pixel-level differences. | ✓ |
| Scatter plot (product vs reference) | 1:1 scatter with regression line. | ✓ |
| Metric summary table | Table with all metrics and pass/fail status. | |
| Histogram of differences | Distribution of pixel-level differences. | |

**User's choice:** Spatial difference map, Scatter plot
**Notes:** Metric summary table is implicit (always included as the core report content). User selected the two figure types to include alongside it.

---

## Claude's Discretion

- DSWx DSWE band index formulas and threshold mapping from HLS to S2 bands
- JRC tile URL pattern and download/caching implementation
- Jinja2 template design and CSS styling for HTML reports
- Internal helper functions for figure generation
- Whether to add `dist` as a CLI subcommand (dist-s1 availability uncertain)
- Test fixture design for DSWx and report generation tests

## Deferred Ideas

None — discussion stayed within phase scope
