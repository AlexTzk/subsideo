# Phase 7: CLI Gaps & Code Cleanup - Research

**Researched:** 2026-04-06
**Domain:** Typer CLI wiring, EGMS auto-fetch, dead code removal
**Confidence:** HIGH

## Summary

Phase 7 is a focused cleanup phase with four discrete tasks: (1) add a `build-db` CLI command that exposes the existing `build_burst_db()` function, (2) add EGMS auto-fetch logic to the `validate --product-type disp` flow mirroring the ASF auto-fetch pattern already implemented in Phase 6 for RTC/CSLC, (3) remove the orphaned `select_utm_epsg()` function from `burst/tiling.py` and its test references, and (4) remove a stale comment in `cli.py`.

All four items are low-risk, code-only changes touching existing modules with established patterns. The `build-db` command follows the same Typer `@app.command()` pattern used by every other subcommand. The EGMS auto-fetch mirrors the ASF auto-fetch block added in Phase 6 (cli.py lines 281-358). The dead code removal is safe because `select_utm_epsg` has zero callers in production code -- all product modules access `burst.epsg` directly.

**Primary recommendation:** Implement all four items in a single plan with 2-3 tasks. The `build-db` CLI and EGMS auto-fetch are the substantive work; the dead code removal and comment cleanup are trivial additions.

## Project Constraints (from CLAUDE.md)

- ruff with line-length 100, target Python 3.10
- isort via ruff with `known-first-party = ["subsideo"]`
- mypy strict mode (but `ignore_missing_imports = true` for GDAL/ISCE3)
- Hatchling build backend, src layout (`src/subsideo/`)
- pytest with `--cov=subsideo --cov-report=term-missing` and 80% coverage minimum
- Lazy imports for conda-forge deps inside function bodies
- Never commit credentials
- Context7 for library docs

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BURST-01 | Library provides an EU-scoped burst database (SQLite) built from ESA burst ID maps | `build_burst_db()` already exists in `burst/db.py`; this phase adds the CLI entry point `subsideo build-db <geojson>` to expose it |
| VAL-04 | Library can compare DISP-S1 output against EGMS EU displacement products (r > 0.92, bias < 3 mm/yr) | `compare_disp()` and `fetch_egms_ortho()` already exist in `validation/compare_disp.py`; this phase wires auto-fetch into the validate CLI when `--egms` is omitted |
</phase_requirements>

## Architecture Patterns

### Current CLI Structure (cli.py)

The CLI follows a consistent pattern:
- Each command is a `@app.command("name")` function
- Lazy imports inside command bodies for heavy deps
- `typer.Option()` for all parameters with help text
- `typer.BadParameter` / `typer.Exit(code=1)` for error handling
- `configure_logging(verbose=verbose)` as first call

### Pattern: ASF Auto-Fetch (Phase 6 precedent)

The ASF auto-fetch in `validate_cmd` (cli.py lines 281-358) is the exact pattern to follow for EGMS auto-fetch:

```python
# When --egms is None and product_type is "disp":
# 1. Extract bbox from product files (reproject UTM -> WGS84)
# 2. Call fetch_egms_ortho(bbox, output_dir)
# 3. Set egms_path to the returned Path
# 4. Wrap in try/except, echo warnings on failure
```

Key design decisions from Phase 6:
- Lazy imports for rasterio/pyproj inside the try block
- Warning on failure, not hard error (graceful degradation)
- Auto-fetch only when the explicit path flag is omitted

### Pattern: build-db CLI Command

The `build_burst_db()` function signature (from `burst/db.py`):

```python
def build_burst_db(
    geojson_source: str | Path,
    output_path: Path | None = None,
    eu_bounds: tuple[float, float, float, float] = (-32.0, 27.0, 45.0, 72.0),
) -> Path:
```

The CLI command needs:
- Required `geojson` argument (Path to ESA burst ID GeoJSON)
- Optional `--output` for custom DB path (defaults to `~/.subsideo/eu_burst_db.sqlite`)
- Optional `--bounds` for custom EU bounding box (advanced usage)
- `--verbose` flag (consistent with other commands)

### Dead Code: select_utm_epsg

**Location:** `src/subsideo/burst/tiling.py` (entire file is this one function)
**Callers in production code:** Zero. All product modules access `BurstRecord.epsg` directly:
- `rtc.py:366` -- `output_epsg = bursts[0].epsg`
- `cslc.py:344` -- `output_epsg = bursts[0].epsg`
- `disp.py:533` -- `output_epsg = bursts[0].epsg`
- `dist.py:319` -- `output_epsg = bursts[0].epsg if bursts else 32632`

**Test callers:** `tests/unit/test_burst_db.py` lines 15, 81-108 (two tests: `test_select_utm_epsg_reads_from_record` and `test_select_utm_epsg_portugal`)

**Decision:** Remove `burst/tiling.py` entirely and remove the two test functions that import from it. The function is a trivial `return burst_record.epsg` wrapper with no additional logic worth preserving.

### Stale Comment

**Location:** `cli.py` lines 42-45:
```python
# ---------------------------------------------------------------------------
# check-env (existing)
# ---------------------------------------------------------------------------
```

The `(existing)` annotation is a leftover from Plan 04 (Phase 4) where check-env was marked as pre-existing while new commands were being added. Replace with a clean section separator matching the style of the "Product subcommands" separator at line 103.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EGMS download | Custom HTTP client | `fetch_egms_ortho()` from `validation/compare_disp.py` | Already implemented, handles EGMStoolkit API |
| Burst DB construction | New DB builder | `build_burst_db()` from `burst/db.py` | Already implemented and tested |
| CLI argument parsing | argparse | typer `@app.command()` | Project standard; all other commands use typer |
| Bbox extraction from raster | Manual GDAL calls | rasterio `.bounds` + pyproj `Transformer` | Pattern already established in ASF auto-fetch block |

## Common Pitfalls

### Pitfall 1: Forgetting EGMStoolkit Lazy Import
**What goes wrong:** `import EGMStoolkit` at module level crashes when EGMStoolkit is not installed.
**Why it happens:** EGMStoolkit is a pip-installable optional dependency.
**How to avoid:** Import inside the try block, same as the ASF auto-fetch pattern. `fetch_egms_ortho` already handles this internally with its own ImportError, but the CLI auto-fetch code path should also wrap the entire block in try/except.
**Warning signs:** ImportError on `subsideo validate` when EGMStoolkit is not installed but user is not requesting DISP validation.

### Pitfall 2: Velocity File Glob Pattern
**What goes wrong:** The EGMS auto-fetch needs to extract bbox from the velocity file, but the glob pattern in cli.py line 385 is `*velocity*.tif` + `*velocity*.h5`.
**Why it happens:** The velocity file naming may vary.
**How to avoid:** Reuse the same glob pattern already in the disp validation block. The bbox extraction should happen after velocity files are found (line 385-387) but before the `egms_path is None` check.

### Pitfall 3: Removing tiling.py Without Updating __init__.py
**What goes wrong:** If `burst/__init__.py` imports from `tiling`, removal causes ImportError.
**How to avoid:** Check `burst/__init__.py` for any re-exports of `select_utm_epsg`.

### Pitfall 4: Build-db Argument vs Option
**What goes wrong:** Using `typer.Option` for the GeoJSON path makes the command verbose (`subsideo build-db --geojson path.geojson`).
**How to avoid:** Use `typer.Argument` for the GeoJSON path since it is required and positional. This matches the success criteria wording: `subsideo build-db <geojson>`.

## Code Examples

### build-db CLI Command

```python
@app.command("build-db")
def build_db_cmd(
    geojson: Path = typer.Argument(..., help="Path to ESA Sentinel-1 burst ID GeoJSON"),
    output: Path = typer.Option(
        None, "--output", "-o", help="Output SQLite path (default: ~/.subsideo/eu_burst_db.sqlite)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug-level logging"),
) -> None:
    """Build the EU burst database from ESA burst ID GeoJSON."""
    from subsideo.utils.logging import configure_logging

    configure_logging(verbose=verbose)
    if not geojson.exists():
        raise typer.BadParameter(f"GeoJSON file not found: {geojson}")
    from subsideo.burst.db import build_burst_db

    db_path = build_burst_db(geojson_source=geojson, output_path=output)
    typer.echo(f"[OK] EU burst database built at {db_path}")
```

### EGMS Auto-Fetch in Validate Command

```python
# Insert before the existing disp validation block (line 382):
if pt == "disp" and egms_path is None:
    velocity_files = sorted(product_dir.glob("*velocity*.tif")) + sorted(
        product_dir.glob("*velocity*.h5")
    )
    if velocity_files:
        try:
            import rasterio
            from pyproj import Transformer

            from subsideo.validation.compare_disp import fetch_egms_ortho

            with rasterio.open(velocity_files[0]) as ds:
                b = ds.bounds
                src_crs = ds.crs
            transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
            x1, y1 = transformer.transform(b.left, b.bottom)
            x2, y2 = transformer.transform(b.right, b.top)
            bbox = (x1, y1, x2, y2)

            egms_dir = out / "egms_reference"
            egms_path = fetch_egms_ortho(bbox=bbox, output_dir=egms_dir)
            typer.echo(f"[OK] Auto-fetched EGMS Ortho reference: {egms_path}")
        except Exception as exc:
            typer.echo(f"[WARNING] EGMS auto-fetch failed: {exc}", err=True)
```

## Files to Modify

| File | Action | Reason |
|------|--------|--------|
| `src/subsideo/cli.py` | Add `build-db` command | BURST-01 CLI gap |
| `src/subsideo/cli.py` | Add EGMS auto-fetch block | VAL-04 auto-fetch |
| `src/subsideo/cli.py` | Clean stale comment at line 42-44 | Orphaned annotation |
| `src/subsideo/burst/tiling.py` | Delete file | Orphaned function |
| `tests/unit/test_burst_db.py` | Remove `select_utm_epsg` import and 2 tests | Dead code cleanup |
| `tests/unit/test_cli.py` | Add `build-db` to help text assertions | New command registration |

## Pre-Removal Verification

Before removing `burst/tiling.py`, verify no imports exist:

| Check | Result |
|-------|--------|
| `src/subsideo/` imports of `select_utm_epsg` | None (grep confirmed) |
| `src/subsideo/` imports of `burst.tiling` | None (grep confirmed) |
| `src/subsideo/burst/__init__.py` re-exports | Need to verify at execution time |
| `tests/` imports | Only `test_burst_db.py` lines 15, 81-108 |

## Open Questions

None. All four items are well-defined with established patterns to follow.

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `src/subsideo/cli.py` (current state, all 452 lines)
- Direct code inspection of `src/subsideo/burst/tiling.py` (16 lines, single function)
- Direct code inspection of `src/subsideo/burst/db.py` (`build_burst_db` signature and implementation)
- Direct code inspection of `src/subsideo/validation/compare_disp.py` (`fetch_egms_ortho` signature)
- Grep results confirming zero production callers of `select_utm_epsg`
- Phase 6 implementation as precedent for auto-fetch pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all existing
- Architecture: HIGH - follows established CLI patterns from Phases 4-6
- Pitfalls: HIGH - based on direct code inspection of the exact files being modified

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable; no external dependencies changing)
