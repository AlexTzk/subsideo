# run_eval_cslc_selfconsist_nam.py — N.Am. CSLC-S1 self-consistency eval
#
# Phase 3 (v1.1) deliverable. Proves CSLC self-consistency across 15-epoch
# SoCal stack (CSLC-03 calibration anchor) + Mojave fallback-chain (CSLC-04
# first-PASS/CALIBRATING wins; BLOCKER on exhaustion of accepted fallbacks).
#
# Produces one cell-level eval-cslc-selfconsist-nam/metrics.json
# (CSLCSelfConsistNAMCellMetrics) + per-AOI P2.1 sanity artifacts.
#
# First-rollout renders as CALIBRATING per D-03 — PASS/FAIL is intentionally
# NOT emitted regardless of measured numbers. Mojave exhaustion surfaces as
# BLOCKER (not a silent FAIL) per CSLC-04 + D-11.
#
# Orchestration:
#   - Declarative AOIS: list[AOIConfig] (D-05 analog for self-consistency)
#   - Per-AOI try/except isolation (D-06 analog)
#   - Mojave fallback-chain: first CALIBRATING/PASS wins; all-FAIL -> BLOCKER
#   - Per-epoch SAFE download + CSLC run (no burst-level parallelism)
#   - Per-AOI whole-pipeline skip + per-stage ensure_resume_safe (D-08 analog)
#   - Cached-SAFE reuse via harness.find_cached_safe (D-02)
#   - Single eval-cslc-selfconsist-nam/metrics.json (CSLCSelfConsistNAMCellMetrics)
#   - P2.1 sanity artifacts: coherence_histogram.png + stable_mask_over_basemap.png
#     + mask_metadata.json per AOI (stable-mask-contamination visual check)
#
# SoCal mandatory constraints (CSLC-03):
#   - burst_id = t144_308029_iw1 (locked from CONCLUSIONS_CSLC_N_AM.md v1.0)
#   - 15-epoch window: 2024-01-13 to 2024-06-29, 12-day S1A POEORB cadence
#   - Amplitude sanity on first epoch vs OPERA N.Am. reference (D-07)
#
# Exit code: 0 for PASS/CALIBRATING/MIXED (first-rollout success per D-03);
#            1 for BLOCKER-only or all-FAIL.
#            MIXED (SoCal CALIBRATING + Mojave BLOCKER) is exit 0 because
#            partial success is acceptable in first rollout — BLOCKER surfaces
#            via matrix_writer warning glyph (D-11), not supervisor exit.
#            Supervisor distinguishes 124 = watchdog timeout.
#
# Makefile target: `make eval-cslc-nam` -> supervisor wraps this script.
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

# SoCal 15 epochs × ~40 min/epoch cold + Mojave fallback-chain worst-case
# (4 × 12 h) + per-stage ensure_resume_safe + supervisor 2x margin.
# Cap matches CONTEXT D-Claude's-Discretion EXPECTED_WALL_S budget.
# Warm re-run: <= 5 min (all epoch CSLCs cached; per-AOI skip).
EXPECTED_WALL_S = 60 * 60 * 16   # 57600s; supervisor AST-parses
CANDIDATE_COHERENCE_MIN = 0.75
CANDIDATE_RESIDUAL_ABS_MAX_MM_YR = 2.0


if __name__ == "__main__":
    import hashlib
    import os
    import platform
    import subprocess
    import sys
    import time
    import traceback
    from dataclasses import dataclass
    from datetime import datetime, timedelta
    from pathlib import Path
    from typing import Literal

    import asf_search as asf
    import earthaccess
    import numpy as np
    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.data.dem import fetch_dem
    from subsideo.data.natural_earth import load_coastline_and_waterbodies
    from subsideo.data.orbits import fetch_orbit
    from subsideo.data.worldcover import fetch_worldcover_class60, load_worldcover_for_bbox
    from subsideo.products.cslc import run_cslc
    from subsideo.validation.compare_cslc import compare_cslc
    from subsideo.validation.harness import (
        bounds_for_burst,
        credential_preflight,
        find_cached_safe,
        select_opera_frame_by_utc_hour,
        validate_safe_path,
    )
    from subsideo.validation.matrix_schema import (
        AOIResult,
        CSLCBlockerEvidence,
        CSLCCandidateBindingResult,
        CSLCCandidateThresholds,
        CSLCSelfConsistNAMCellMetrics,
        MetaJson,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
    )
    from subsideo.validation.selfconsistency import (
        coherence_stats,
        compute_ifg_coherence_stack,
        compute_residual_velocity,
        residual_mean_velocity,
    )
    from subsideo.validation.stable_terrain import build_stable_mask

    # Type aliases
    AOIStatus = Literal["PASS", "FAIL", "CALIBRATING", "BLOCKER", "SKIPPED"]
    CSLCCellStatus = Literal["PASS", "FAIL", "CALIBRATING", "MIXED", "BLOCKER"]

    load_dotenv()

    credential_preflight([
        "EARTHDATA_USERNAME",
        "EARTHDATA_PASSWORD",
    ])

    # -- Configuration -------------------------------------------------------

    @dataclass(frozen=True)
    class AOIConfig:
        """Per-AOI declarative config (D-05 analog for self-consistency eval)."""

        aoi_name: str                       # "SoCal" | "Mojave" | "Iberian"
        regime: str                         # e.g. "SoCal-Mediterranean"
        burst_id: str                       # JPL lowercase; "" for Mojave/Iberian parent rows
        sensing_window: tuple[datetime, ...]  # Always 15 entries per D-PATTERNS invariant
        output_epsg: int                    # UTM zone
        centroid_lat: float
        cached_safe_search_dirs: tuple[Path, ...]
        fallback_chain: tuple["AOIConfig", ...] = ()  # empty for leaves
        # BLOCKER 4 fix: per-AOI attribute that drives amplitude-sanity gating.
        # SoCal + bounded Mojave fallback leaves = True (D-07/D-09 runs
        # compare_cslc or records OPERA frame-search evidence on first epoch).
        # Mojave parent = False (inherited default; parent status folds from attempts[]).
        # Replaces a prior aoi_name-based literal conditional so the EU fork
        # (Plan 03-04) can set True on IberianAOI without editing the leaf-path
        # conditional — the flag is the only gate, not any aoi_name string.
        run_amplitude_sanity: bool = False

    # OPERA burst DB (compass v0.5.6 requires a real file — passing None trips
    # os.path.isfile(None) inside compass.utils.geo_runconfig.GeoRunConfig.load_from_yaml
    # at line 71). We fetch opera-adt/burst_db v0.9.0's 23MB opera-burst-bbox-only
    # sqlite on first run and cache at ~/.subsideo/opera_burst_bbox.sqlite3.
    OPERA_BURST_DB_URL: str = (
        "https://github.com/opera-adt/burst_db/releases/download/v0.9.0/"
        "opera-burst-bbox-only.sqlite3.zip"
    )
    OPERA_BURST_DB_PATH: Path = Path.home() / ".subsideo" / "opera_burst_bbox.sqlite3"

    def _ensure_opera_burst_db() -> Path:
        """Download opera-adt/burst_db v0.9.0 opera-burst-bbox-only.sqlite3 on first use."""
        import io
        import zipfile
        from urllib.request import urlopen

        if OPERA_BURST_DB_PATH.exists():
            return OPERA_BURST_DB_PATH
        OPERA_BURST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading OPERA burst DB from {} (23 MB zip)...", OPERA_BURST_DB_URL)
        with urlopen(OPERA_BURST_DB_URL, timeout=300) as resp:
            buf = io.BytesIO(resp.read())
        with zipfile.ZipFile(buf) as zf:
            names = [n for n in zf.namelist() if n.endswith(".sqlite3")]
            if not names:
                raise RuntimeError(f"No .sqlite3 member in {OPERA_BURST_DB_URL}")
            with zf.open(names[0]) as src, open(OPERA_BURST_DB_PATH, "wb") as dst:
                dst.write(src.read())
        logger.info("Cached OPERA burst DB at {} ({} bytes)",
                    OPERA_BURST_DB_PATH, OPERA_BURST_DB_PATH.stat().st_size)
        return OPERA_BURST_DB_PATH

    # -- Locked sensing windows --------------------------------------------
    #
    # 15-epoch SoCal sensing window for burst t144_308029_iw1.
    # Verified via ASF search against the real burst footprint on 2026-04-24
    # (the 03-02 probe emitted fabricated 12-day-cadence dates starting
    # 2024-01-13T14:01:16Z that did NOT correspond to actual acquisitions —
    # this tuple is the ground truth pulled from asf_search with
    # relativeOrbit=144 + intersectsWith=burst.footprint). All S1A POEORB,
    # 12-day cadence, covers 168 days.
    SOCAL_EPOCHS: tuple[datetime, ...] = (
        datetime(2024, 1, 8, 14, 1, 14),
        datetime(2024, 1, 20, 14, 1, 14),
        datetime(2024, 2, 1, 14, 1, 13),
        datetime(2024, 2, 13, 14, 1, 13),
        datetime(2024, 2, 25, 14, 1, 13),
        datetime(2024, 3, 8, 14, 1, 13),
        datetime(2024, 3, 20, 14, 1, 13),
        datetime(2024, 4, 1, 14, 1, 14),
        datetime(2024, 4, 13, 14, 1, 13),
        datetime(2024, 4, 25, 14, 1, 14),
        datetime(2024, 5, 7, 14, 1, 14),
        datetime(2024, 5, 19, 14, 1, 14),
        datetime(2024, 5, 31, 14, 1, 14),
        datetime(2024, 6, 12, 14, 1, 13),
        datetime(2024, 6, 24, 14, 1, 13),
    )

    SoCalAOI = AOIConfig(
        aoi_name="SoCal",
        regime="SoCal-Mediterranean",
        burst_id="t144_308029_iw1",
        sensing_window=SOCAL_EPOCHS,
        output_epsg=32611,   # UTM 11N
        centroid_lat=34.8,
        cached_safe_search_dirs=(
            Path("eval-cslc-selfconsist-nam/input"),
            Path("eval-cslc/input"),    # v1.0 cache (may contain first epoch)
            Path("eval-rtc/input"),     # v1.0 RTC cache
        ),
        run_amplitude_sanity=True,  # SoCal runs D-07 amplitude sanity on first epoch
    )

    # Per-AOI 15-epoch sensing windows (locked from
    # .planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md;
    # section anchors MOJAVE_COSO_EPOCHS / MOJAVE_PAHRANAGAT_EPOCHS / etc.).
    # BLOCKER 1 fix: every Mojave fallback uses a 15-epoch stack in the same
    # shape as SoCal — compute_residual_velocity requires >=3 epochs;
    # compute_ifg_coherence_stack requires >=2 epochs. The fallback policy
    # (CONTEXT D-11) picks WHICH burst; it does not relax the stack shape.

    # Phase 8 regenerated these AOIs via live ASF search. Hualapai was rejected
    # in the v1.2 artifact because H1 2024 returned only 14 unique S1A dates,
    # so it is not wired into the runnable fallback chain.

    # ### MOJAVE_COSO_EPOCHS — Mojave/Coso-Searles (track 064)
    MOJAVE_COSO_EPOCHS: tuple[datetime, ...] = (
        datetime(2023, 12, 22, 1, 51, 11),
        datetime(2024, 1, 3, 1, 51, 11),
        datetime(2024, 1, 15, 1, 51, 10),
        datetime(2024, 1, 27, 1, 51, 10),
        datetime(2024, 2, 8, 1, 51, 10),
        datetime(2024, 2, 20, 1, 51, 10),
        datetime(2024, 3, 3, 1, 51, 10),
        datetime(2024, 3, 15, 1, 51, 10),
        datetime(2024, 3, 27, 1, 51, 10),
        datetime(2024, 4, 8, 1, 51, 11),
        datetime(2024, 4, 20, 1, 51, 11),
        datetime(2024, 5, 2, 1, 51, 11),
        datetime(2024, 5, 14, 1, 51, 11),
        datetime(2024, 5, 26, 1, 51, 11),
        datetime(2024, 6, 19, 1, 51, 10),
    )

    # ### MOJAVE_PAHRANAGAT_EPOCHS — Mojave/Pahranagat (track 173)
    MOJAVE_PAHRANAGAT_EPOCHS: tuple[datetime, ...] = (
        datetime(2024, 1, 10, 13, 43, 40),
        datetime(2024, 1, 22, 13, 43, 40),
        datetime(2024, 2, 3, 13, 43, 40),
        datetime(2024, 2, 15, 13, 43, 39),
        datetime(2024, 2, 27, 13, 43, 39),
        datetime(2024, 3, 10, 13, 43, 39),
        datetime(2024, 3, 22, 13, 43, 40),
        datetime(2024, 4, 3, 13, 43, 40),
        datetime(2024, 4, 15, 13, 43, 40),
        datetime(2024, 4, 27, 13, 43, 41),
        datetime(2024, 5, 9, 13, 43, 41),
        datetime(2024, 5, 21, 13, 43, 40),
        datetime(2024, 6, 2, 13, 43, 40),
        datetime(2024, 6, 14, 13, 43, 40),
        datetime(2024, 6, 26, 13, 43, 39),
    )

    # ### MOJAVE_AMARGOSA_EPOCHS — Mojave/Amargosa (track 064)
    MOJAVE_AMARGOSA_EPOCHS: tuple[datetime, ...] = (
        datetime(2023, 12, 22, 1, 51, 11),
        datetime(2024, 1, 3, 1, 51, 11),
        datetime(2024, 1, 15, 1, 51, 10),
        datetime(2024, 1, 27, 1, 51, 10),
        datetime(2024, 2, 8, 1, 51, 10),
        datetime(2024, 2, 20, 1, 51, 10),
        datetime(2024, 3, 3, 1, 51, 10),
        datetime(2024, 3, 15, 1, 51, 10),
        datetime(2024, 3, 27, 1, 51, 10),
        datetime(2024, 4, 8, 1, 51, 11),
        datetime(2024, 4, 20, 1, 51, 11),
        datetime(2024, 5, 2, 1, 51, 11),
        datetime(2024, 5, 14, 1, 51, 11),
        datetime(2024, 5, 26, 1, 51, 11),
        datetime(2024, 6, 19, 1, 51, 10),
    )

    # Mojave fallback chain — probe-locked order (D-11, highest score first):
    # Attempt 1: Coso/Searles (score 302.40)
    # Attempt 2: Pahranagat   (score 135.30)
    # Attempt 3: Amargosa     (score 224.75)
    # Rejected: Hualapai (ASF returned 14/15 unique dates; see v1.2 artifact)
    _MOJAVE_FALLBACKS: tuple[AOIConfig, ...] = (
        AOIConfig(
            aoi_name="Mojave/Coso-Searles",
            regime="desert-bedrock-playa-adjacent",
            burst_id="t064_135527_iw2",
            sensing_window=MOJAVE_COSO_EPOCHS,
            output_epsg=32611,    # UTM 11N
            centroid_lat=35.85,
            cached_safe_search_dirs=(Path("eval-cslc-selfconsist-nam/input"),),
            run_amplitude_sanity=True,
        ),
        AOIConfig(
            aoi_name="Mojave/Pahranagat",
            regime="desert-bedrock",
            burst_id="t173_370296_iw2",
            sensing_window=MOJAVE_PAHRANAGAT_EPOCHS,
            output_epsg=32611,    # UTM 11N
            centroid_lat=37.27,
            cached_safe_search_dirs=(Path("eval-cslc-selfconsist-nam/input"),),
            run_amplitude_sanity=True,
        ),
        AOIConfig(
            aoi_name="Mojave/Amargosa",
            regime="desert-bedrock-playa-adjacent",
            burst_id="t064_135530_iw3",
            sensing_window=MOJAVE_AMARGOSA_EPOCHS,
            output_epsg=32611,    # UTM 11N
            centroid_lat=36.47,
            cached_safe_search_dirs=(Path("eval-cslc-selfconsist-nam/input"),),
            run_amplitude_sanity=True,
        ),
    )

    MojaveAOI = AOIConfig(
        aoi_name="Mojave",
        regime="desert-fallback-chain",
        burst_id="",                  # parent has no burst_id
        sensing_window=(),            # parent has no epochs; delegates to fallback_chain
        output_epsg=0,
        centroid_lat=35.85,
        cached_safe_search_dirs=(Path("eval-cslc-selfconsist-nam/input"),),
        fallback_chain=_MOJAVE_FALLBACKS,
    )

    AOIS: list[AOIConfig] = [SoCalAOI, MojaveAOI]

    # -- Cache layout --------------------------------------------------------

    CACHE = Path("eval-cslc-selfconsist-nam")
    for _sub in ("input", "output", "opera_reference", "dem", "orbits",
                 "worldcover", "coastline", "sanity"):
        (CACHE / _sub).mkdir(parents=True, exist_ok=True)

    run_started = time.time()
    run_started_iso = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%SZ")

    auth = earthaccess.login(strategy="environment")  # noqa: F841

    # -- Helpers -------------------------------------------------------------

    def sha256_of_file(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def get_git_sha() -> tuple[str, bool]:
        try:
            sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip()
            dirty = bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], text=True
                ).strip()
            )
            return sha, dirty
        except Exception:  # noqa: BLE001
            return "unknown", True

    def _safe_granule_for_epoch(burst_id: str, epoch: datetime) -> str:
        """Build a granule ID search key for the SLC containing burst_id at epoch.

        Returns a partial granule name pattern for find_cached_safe to match
        against cached SAFE zip filenames. Format: S1A_IW_SLC_...
        """
        # Use date-based pattern that ASF granule IDs follow
        date_str = epoch.strftime("%Y%m%d")
        return f"S1A_IW_SLC__{date_str}"

    def _download_safe_for_epoch(
        burst_id: str, epoch: datetime, dest_dir: Path
    ) -> Path:
        """Download the Sentinel-1 SAFE containing burst_id at epoch from ASF.

        Filters ASF search by relativeOrbit (parsed from burst_id) + the burst
        footprint polygon so we don't accidentally grab a different orbit that
        happens to be acquiring at the same UTC minute (e.g. track 42 when the
        target is track 144). Validates the zip before returning; corrupt
        partial downloads are deleted + re-raised.
        """
        from shapely.geometry import box as _shapely_box

        # Parse track from burst_id (format: t{NNN}_{NNNNNN}_{iwN})
        track_num = int(burst_id.split("_")[0].lstrip("t"))

        # Burst footprint (light buffer to be inclusive of frame edges)
        bounds = bounds_for_burst(burst_id, buffer_deg=0.1)
        wkt = _shapely_box(*bounds).wkt

        window_start = (epoch - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        window_end = (epoch + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

        results = asf.search(
            platform=asf.PLATFORM.SENTINEL1,
            processingLevel="SLC",
            beamMode="IW",
            relativeOrbit=track_num,
            intersectsWith=wkt,
            start=window_start,
            end=window_end,
            maxResults=10,
        )
        if not results:
            raise RuntimeError(
                f"No S1 SLC found on ASF for {burst_id} "
                f"(track={track_num}, bbox={bounds}) around {epoch}"
            )

        # S1 IW SLCs are cut into ~25s slices per pass and the ±10 min
        # window usually matches 2+ slices per orbit. Pick the slice whose
        # (startTime, stopTime) contains the target epoch; the burst can
        # only live in one slice, and picking the wrong one causes compass
        # to fail at runconfig.correlate_burst_to_orbit with "Could not
        # find any of the burst IDs in the provided safe files". SoCal
        # happened to work with results[0] because its burst aligns with
        # the first slice returned; Iberian Meseta doesn't.
        scene = None
        for r in results:
            try:
                start_iso = r.properties["startTime"].rstrip("Z").split(".")[0]
                stop_iso = r.properties["stopTime"].rstrip("Z").split(".")[0]
                r_start = datetime.fromisoformat(start_iso)
                r_stop = datetime.fromisoformat(stop_iso)
            except (KeyError, ValueError):
                continue
            if r_start <= epoch <= r_stop:
                scene = r
                break
        if scene is None:
            raise RuntimeError(
                f"No ASF slice for {burst_id} contains epoch {epoch.isoformat()} "
                f"(candidates: {[r.properties.get('fileID', '?') for r in results]})"
            )
        granule_id = str(scene.properties["fileID"]).removesuffix("-SLC")
        safe_path = dest_dir / f"{granule_id}.zip"
        if not safe_path.exists():
            logger.info("Downloading SAFE from ASF (~4 GB): {}", granule_id)
            session = asf.ASFSession().auth_with_creds(
                username=os.environ["EARTHDATA_USERNAME"],
                password=os.environ["EARTHDATA_PASSWORD"],
            )
            scene.download(path=str(dest_dir), session=session)
            zips = sorted(dest_dir.glob(f"{granule_id}*.zip"))
            if not zips:
                raise RuntimeError(
                    f"ASF download failed for {granule_id}: no zip in {dest_dir}"
                )
            safe_path = zips[-1]

        if not validate_safe_path(safe_path, remove_invalid=True):
            raise RuntimeError(
                f"Downloaded SAFE {safe_path.name} failed integrity validation; "
                "deleted if it was an invalid zip"
            )
        return safe_path

    def _compute_slope_deg(dem_path: Path) -> tuple[np.ndarray, object, object]:
        """Compute slope in degrees from a DEM GeoTIFF via numpy.gradient.

        Returns (slope_deg, transform, crs) so the caller can reproject other
        rasters (WorldCover) onto this grid before feeding build_stable_mask.
        """
        import rasterio  # lazy

        with rasterio.open(dem_path) as src:
            dem = src.read(1).astype(np.float32)
            pixel_m = abs(src.transform.a)
            dem_transform = src.transform
            dem_crs = src.crs

        dz_dy, dz_dx = np.gradient(dem, pixel_m)
        slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
        slope_deg = np.degrees(slope_rad).astype(np.float32)
        return slope_deg, dem_transform, dem_crs

    def _reproject_worldcover_to_dem_grid(
        wc_data: np.ndarray,
        wc_transform: object,
        wc_crs: object,
        *,
        dst_shape: tuple[int, int],
        dst_transform: object,
        dst_crs: object,
    ) -> np.ndarray:
        """Reproject WorldCover onto the DEM grid (nearest neighbour — class labels).

        WorldCover ships in EPSG:4326 10m; the DEM is in the CSLC output_epsg
        (UTM 30m). build_stable_mask requires both arrays on the same grid.
        """
        from rasterio.warp import Resampling, reproject  # lazy

        dst = np.zeros(dst_shape, dtype=wc_data.dtype)
        reproject(
            source=wc_data,
            destination=dst,
            src_transform=wc_transform,
            src_crs=wc_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,  # class labels — never interpolate
        )
        return dst

    def _write_sanity_artifacts(
        aoi_name: str,
        stable_mask: np.ndarray,
        coherence_stack: np.ndarray,
        transform: object,
        crs: object,
        out_dir: Path,
        stable_mask_diagnostics: dict[str, object] | None = None,
    ) -> None:
        """Write P2.1 stable-mask sanity artifacts for one AOI.

        Artifacts (per-AOI, under eval-cslc-selfconsist-nam/sanity/<aoi>/):
          - coherence_histogram.png: histogram of per-pixel mean coherence
            over stable mask + red vertical line at 0.7 gate threshold.
          - stable_mask_over_basemap.png: stable mask rendered as a simple
            overlay (grayscale DEM or Natural Earth land polygon background).
          - mask_metadata.json: {n_stable_pixels, bounding_box, regime,
            worldcover_class_60_count (approximated), final_stable_count,
            stable_pct_of_aoi}.

        P2.1 mitigation: bimodal coherence histogram indicates mask
        contamination (dune/playa/fallow field pixels). Investigator checks
        these artifacts before writing CONCLUSIONS.
        """
        import json as json_mod  # noqa: I001  # lazy
        import matplotlib  # lazy

        matplotlib.use("Agg")  # must precede pyplot import (sets non-interactive backend)
        import matplotlib.pyplot as plt  # lazy (after Agg backend set)

        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Coherence histogram
        per_pixel_mean_coh = coherence_stack.mean(axis=0)  # (H, W)
        stable_coh = per_pixel_mean_coh[stable_mask]

        fig, ax = plt.subplots(figsize=(8, 4))
        if stable_coh.size > 0:
            ax.hist(stable_coh, bins=50, color="steelblue", alpha=0.7,
                    label=f"n={stable_coh.size}")
            ax.axvline(0.7, color="red", linewidth=1.5, linestyle="--",
                       label="gate = 0.7")
            ax.set_xlabel("Per-pixel mean coherence")
            ax.set_ylabel("Count")
            ax.set_title(f"{aoi_name} — coherence histogram (stable mask)")
            ax.legend()
        else:
            ax.text(0.5, 0.5, "No stable pixels", transform=ax.transAxes,
                    ha="center", va="center")
            ax.set_title(f"{aoi_name} — coherence histogram (EMPTY MASK)")
        fig.tight_layout()
        fig.savefig(out_dir / "coherence_histogram.png", dpi=120)
        plt.close(fig)

        # 2. Stable mask over basemap (simple binary image)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.imshow(stable_mask, cmap="Greens", aspect="auto", origin="upper",
                  vmin=0, vmax=1, interpolation="nearest")
        ax.set_title(f"{aoi_name} — stable mask (green=stable, black=excluded)")
        ax.set_xlabel("x pixel")
        ax.set_ylabel("y pixel")
        fig.tight_layout()
        fig.savefig(out_dir / "stable_mask_over_basemap.png", dpi=120)
        plt.close(fig)

        # 3. Mask metadata JSON (P2.1 machine-readable summary)
        h, w = stable_mask.shape
        n_total = h * w
        n_stable = int(stable_mask.sum())
        metadata = {
            "aoi_name": aoi_name,
            "n_stable_pixels": n_stable,
            "total_pixels": n_total,
            "stable_pct_of_aoi": round(100.0 * n_stable / n_total, 2) if n_total > 0 else 0.0,
            "mask_shape": [h, w],
            # Diagnostics for P2.1 investigation
            "mean_coherence_stable": (
                float(stable_coh.mean()) if stable_coh.size > 0 else None
            ),
            "median_coherence_stable": (
                float(np.median(stable_coh)) if stable_coh.size > 0 else None
            ),
            "bounding_box": "derived_from_burst_bounds",
            "regime": "from_AOIConfig",
        }
        if stable_mask_diagnostics:
            metadata.update(stable_mask_diagnostics)
        (out_dir / "mask_metadata.json").write_text(
            json_mod.dumps(metadata, indent=2)
        )
        logger.info(
            "{} sanity artifacts written to {} (n_stable={})",
            aoi_name, out_dir, n_stable,
        )

    def _collect_input_hashes(cfg: AOIConfig) -> dict[str, str]:
        """SHA256 hashes of primary inputs for meta.json provenance."""
        hashes: dict[str, str] = {}
        if cfg.burst_id:
            # DEM
            dem_dir = CACHE / "dem" / cfg.aoi_name
            for p in sorted(dem_dir.glob("*.tif"))[:1]:
                hashes[f"{cfg.aoi_name}_dem_sha256"] = sha256_of_file(p)
            # OPERA reference (SoCal only)
            ref_dir = CACHE / "opera_reference" / cfg.aoi_name
            for p in sorted(ref_dir.glob("*.h5"))[:1]:
                hashes[f"{cfg.aoi_name}_opera_ref_sha256"] = sha256_of_file(p)
        return hashes

    def _opera_burst_upper(burst_id: str) -> str:
        """Convert JPL lowercase burst ID to OPERA granule burst token."""
        parts = burst_id.split("_")
        return f"T{parts[0][1:]}-{parts[1]}-{parts[2].upper()}"

    def _build_opera_frame_search(
        cfg: AOIConfig,
        epoch: datetime,
        ref_h5_candidates: list[Path],
    ) -> dict[str, str | int | float | bool | None]:
        """Build schema-valid OPERA frame-search evidence for amplitude sanity."""
        opera_burst_upper = _opera_burst_upper(cfg.burst_id)
        opera_ref_h5 = ref_h5_candidates[0] if ref_h5_candidates else None
        return {
            "aoi_name": cfg.aoi_name,
            "burst_id": cfg.burst_id,
            "epoch_iso": epoch.isoformat(),
            "opera_burst_upper": opera_burst_upper,
            "granule_pattern": f"OPERA_L2_CSLC-S1_{opera_burst_upper}*",
            "reference_h5_count": len(ref_h5_candidates),
            "selected_reference_h5": str(opera_ref_h5) if ref_h5_candidates else None,
        }

    def _ensure_opera_reference_for_first_epoch(
        cfg: AOIConfig,
    ) -> tuple[list[Path], dict[str, str | int | float | bool | None]]:
        """Ensure first-epoch OPERA reference if available and return search evidence."""
        epoch = cfg.sensing_window[0]
        ref_aoi_dir = CACHE / "opera_reference" / cfg.aoi_name
        ref_aoi_dir.mkdir(parents=True, exist_ok=True)
        ref_h5_candidates = sorted(ref_aoi_dir.glob("*.h5"))
        if not ref_h5_candidates:
            opera_burst_upper = _opera_burst_upper(cfg.burst_id)
            ref_results = earthaccess.search_data(
                short_name="OPERA_L2_CSLC-S1_V1",
                temporal=(
                    (epoch - timedelta(hours=1)).strftime("%Y-%m-%d"),
                    (epoch + timedelta(hours=1)).strftime("%Y-%m-%d"),
                ),
                granule_name=f"OPERA_L2_CSLC-S1_{opera_burst_upper}*",
            )
            if ref_results:
                # earthaccess DataGranule carries sensing time deep inside
                # umm['TemporalExtent']['RangeDateTime']['BeginningDateTime'];
                # select_opera_frame_by_utc_hour wants a flat
                # {'sensing_datetime': iso_str} dict per candidate, so map.
                ref_metadata = [
                    {
                        "sensing_datetime": (
                            g["umm"]["TemporalExtent"]
                            ["RangeDateTime"]["BeginningDateTime"]
                        ),
                        "_granule": g,
                    }
                    for g in ref_results
                ]
                chosen_meta = select_opera_frame_by_utc_hour(
                    epoch, ref_metadata, tolerance_hours=1.0
                )
                earthaccess.download([chosen_meta["_granule"]], str(ref_aoi_dir))
                ref_h5_candidates = sorted(ref_aoi_dir.glob("*.h5"))
        return ref_h5_candidates, _build_opera_frame_search(
            cfg, epoch, ref_h5_candidates
        )

    # -- Cell-status resolver ------------------------------------------------

    def _resolve_cell_status(rows: list[AOIResult]) -> CSLCCellStatus:
        """Aggregate per-AOI statuses into a cell-level status.

        Rules (D-03 + D-11):
          - All CALIBRATING -> CALIBRATING
          - CALIBRATING + BLOCKER mix -> MIXED (partial success, exit 0)
          - All BLOCKER -> BLOCKER (exit 1)
          - Any FAIL -> FAIL
          - All PASS (post-BINDING) -> PASS
          - PASS + CALIBRATING mix -> MIXED
        """
        statuses = {r.status for r in rows}
        if statuses == {"CALIBRATING"}:
            return "CALIBRATING"
        if "BLOCKER" in statuses and "CALIBRATING" in statuses:
            return "MIXED"
        if statuses == {"BLOCKER"}:
            return "BLOCKER"
        if statuses == {"PASS"}:
            return "PASS"
        if "PASS" in statuses and statuses <= {"PASS", "CALIBRATING"}:
            return "MIXED"
        if "FAIL" in statuses:
            return "FAIL"
        return "FAIL"

    def _candidate_binding_for_pq(
        pq: ProductQualityResultJson | None,
    ) -> CSLCCandidateBindingResult:
        thresholds = CSLCCandidateThresholds(
            coherence_median_of_persistent_min=CANDIDATE_COHERENCE_MIN,
            residual_mm_yr_abs_max=CANDIDATE_RESIDUAL_ABS_MAX_MM_YR,
        )
        if pq is None:
            return CSLCCandidateBindingResult(verdict="BINDING BLOCKER", thresholds=thresholds)
        measurements = pq.measurements
        coh = float(measurements.get("coherence_median_of_persistent", float("nan")))
        resid = abs(float(measurements.get("residual_mm_yr", float("nan"))))
        verdict = (
            "BINDING PASS"
            if (
                np.isfinite(coh)
                and np.isfinite(resid)
                and coh >= CANDIDATE_COHERENCE_MIN
                and resid <= CANDIDATE_RESIDUAL_ABS_MAX_MM_YR
            )
            else "BINDING FAIL"
        )
        return CSLCCandidateBindingResult(verdict=verdict, thresholds=thresholds)

    def _candidate_binding_for_rows(rows: list[AOIResult]) -> CSLCCandidateBindingResult:
        thresholds = CSLCCandidateThresholds(
            coherence_median_of_persistent_min=CANDIDATE_COHERENCE_MIN,
            residual_mm_yr_abs_max=CANDIDATE_RESIDUAL_ABS_MAX_MM_YR,
        )
        verdicts = [r.candidate_binding.verdict for r in rows if r.candidate_binding is not None]
        if len(verdicts) != len(rows) or any(v == "BINDING BLOCKER" for v in verdicts):
            return CSLCCandidateBindingResult(
                verdict="BINDING BLOCKER",
                thresholds=thresholds,
                blocker=CSLCBlockerEvidence(
                    reason_code="required_aoi_binding_blocker",
                    evidence={
                        "blocked_aoi_count": sum(1 for v in verdicts if v == "BINDING BLOCKER"),
                        "missing_candidate_binding_count": len(rows) - len(verdicts),
                        "total_required_aoi": len(rows),
                    },
                ),
            )
        verdict = "BINDING FAIL" if any(v == "BINDING FAIL" for v in verdicts) else "BINDING PASS"
        return CSLCCandidateBindingResult(verdict=verdict, thresholds=thresholds)

    def _worst_pq(rows: list[AOIResult]) -> dict[str, float | str]:
        """Compute worst-case product-quality aggregate across AOIs with PQ data."""
        pq_rows = [r for r in rows if r.product_quality is not None
                   and r.product_quality.measurements]
        if not pq_rows:
            return {
                "worst_coherence_median_of_persistent": -1.0,
                "worst_residual_mm_yr": -1.0,
                "worst_aoi": "(none)",
            }
        # Worst = lowest coherence (gate is a minimum)
        worst_coh_row = min(
            pq_rows,
            key=lambda r: r.product_quality.measurements.get(  # type: ignore[union-attr]
                "coherence_median_of_persistent", 1.0
            ),
        )
        worst_res_row = max(
            pq_rows,
            key=lambda r: abs(
                r.product_quality.measurements.get("residual_mm_yr", 0.0)  # type: ignore[union-attr]
            ),
        )
        return {
            "worst_coherence_median_of_persistent": float(
                worst_coh_row.product_quality.measurements.get(  # type: ignore[union-attr]
                    "coherence_median_of_persistent", -1.0
                )
            ),
            "worst_residual_mm_yr": float(
                worst_res_row.product_quality.measurements.get("residual_mm_yr", -1.0)  # type: ignore[union-attr]
            ),
            "worst_aoi": worst_coh_row.aoi_name,
        }

    def _worst_ra(rows: list[AOIResult]) -> dict[str, float | str]:
        """Compute worst-case reference-agreement aggregate (SoCal only; Mojave null)."""
        ra_rows = [r for r in rows if r.reference_agreement is not None
                   and r.reference_agreement.measurements]
        if not ra_rows:
            return {
                "worst_amp_r": -1.0,
                "worst_amp_rmse_db": -1.0,
                "worst_aoi": "(none)",
            }
        worst_r_row = min(
            ra_rows,
            key=lambda r: r.reference_agreement.measurements.get("amp_r", 1.0),  # type: ignore[union-attr]
        )
        worst_rmse_row = max(
            ra_rows,
            key=lambda r: r.reference_agreement.measurements.get("amp_rmse_db", 0.0),  # type: ignore[union-attr]
        )
        return {
            "worst_amp_r": float(
                worst_r_row.reference_agreement.measurements.get("amp_r", -1.0)  # type: ignore[union-attr]
            ),
            "worst_amp_rmse_db": float(
                worst_rmse_row.reference_agreement.measurements.get("amp_rmse_db", -1.0)  # type: ignore[union-attr]
            ),
            "worst_aoi": worst_r_row.aoi_name,
        }

    # -- Per-AOI pipeline ----------------------------------------------------

    def process_aoi(cfg: AOIConfig) -> AOIResult:
        """Run the CSLC self-consistency pipeline for one AOI; return AOIResult.

        For Mojave (cfg.fallback_chain non-empty): recursively attempts each
        candidate until a PASS/CALIBRATING result is found. All-FAIL ->
        parent status = BLOCKER.

        For leaf AOIs (SoCal, Mojave/Coso-Searles, etc.): runs 11-stage
        pipeline: WorldCover -> DEM+slope -> Natural Earth -> stable_mask ->
        per-epoch SAFE+orbit+CSLC -> IFG coherence stack -> residual velocity
        -> amplitude sanity (gated on cfg.run_amplitude_sanity) ->
        sanity artifacts -> AOIResult(CALIBRATING).
        """
        # Handle Mojave fallback-chain recursion
        if cfg.fallback_chain:
            attempts: list[AOIResult] = []
            for idx, candidate in enumerate(cfg.fallback_chain, start=1):
                try:
                    child = process_aoi(candidate)   # leaf path; no recursion
                    child = child.model_copy(update={"attempt_index": idx})
                    attempts.append(child)
                    if child.status in ("PASS", "CALIBRATING"):
                        logger.info(
                            "{} attempt #{}: {} — {}",
                            cfg.aoi_name, idx, candidate.aoi_name, child.status,
                        )
                        # First PASS/CALIBRATING wins; remaining candidates skipped
                        break
                except Exception as e:  # noqa: BLE001
                    tb = traceback.format_exc()
                    logger.error(
                        "{} attempt #{} ({}) FAIL: {}",
                        cfg.aoi_name, idx, candidate.aoi_name, e,
                    )
                    attempts.append(AOIResult(
                        aoi_name=candidate.aoi_name,
                        regime=candidate.regime,
                        burst_id=candidate.burst_id,
                        status="FAIL",
                        attempt_index=idx,
                        reason=f"{type(e).__name__}: {e}",
                        candidate_binding=CSLCCandidateBindingResult(
                            verdict="BINDING BLOCKER",
                            thresholds=CSLCCandidateThresholds(),
                            blocker=CSLCBlockerEvidence(
                                reason_code="aoi_processing_failed",
                                evidence={"error": repr(e)},
                            ),
                        ),
                        error=repr(e),
                        traceback=tb,
                    ))

            # Parent status: first CALIBRATING/PASS attempt wins; all-FAIL -> BLOCKER
            first_success = next(
                (a for a in attempts if a.status in ("PASS", "CALIBRATING")), None
            )
            if first_success is not None:
                parent_status: AOIStatus = first_success.status
                parent_pq = first_success.product_quality
                parent_ra = first_success.reference_agreement
            else:
                parent_status = "BLOCKER"
                parent_pq, parent_ra = None, None

            return AOIResult(
                aoi_name=cfg.aoi_name,
                regime=cfg.regime,
                burst_id=None,
                status=parent_status,
                attempts=attempts,
                product_quality=parent_pq,
                reference_agreement=parent_ra,
                candidate_binding=(
                    first_success.candidate_binding
                    if first_success is not None
                    else CSLCCandidateBindingResult(
                        verdict="BINDING BLOCKER",
                        thresholds=CSLCCandidateThresholds(),
                        blocker=CSLCBlockerEvidence(
                            reason_code="aoi_processing_failed",
                            evidence={"error": f"All {len(cfg.fallback_chain)} fallbacks FAILed"},
                        ),
                    )
                ),
                reason=(
                    None if first_success
                    else f"All {len(cfg.fallback_chain)} fallbacks FAILed"
                ),
            )

        # Leaf path: single-AOI processing
        logger.info("Processing leaf AOI {} (burst {})", cfg.aoi_name, cfg.burst_id)

        # 1. WorldCover
        bounds = bounds_for_burst(cfg.burst_id, buffer_deg=0.5)
        wc_out = CACHE / "worldcover"
        wc_out.mkdir(parents=True, exist_ok=True)
        wc_tiles_dir = fetch_worldcover_class60(bounds, out_dir=wc_out)
        wc_data, wc_transform, wc_crs = load_worldcover_for_bbox(
            bounds, tiles_dir=wc_tiles_dir
        )

        # 2. DEM + slope
        dem_aoi_dir = CACHE / "dem" / cfg.aoi_name
        dem_aoi_dir.mkdir(parents=True, exist_ok=True)
        dem_tifs = sorted(dem_aoi_dir.glob("*.tif"))
        if dem_tifs:
            dem_path = dem_tifs[0]
            logger.info("DEM cached for {}: {}", cfg.aoi_name, dem_path.name)
        else:
            dem_path, _ = fetch_dem(
                bounds=list(bounds),
                output_epsg=cfg.output_epsg,
                output_dir=dem_aoi_dir,
            )
            logger.info("DEM fetched for {}: {}", cfg.aoi_name, dem_path.name)
        slope_deg, dem_transform, dem_crs = _compute_slope_deg(dem_path)

        # 3. Align WorldCover onto the DEM grid (WC is EPSG:4326 10m; DEM is UTM 30m)
        wc_on_dem = _reproject_worldcover_to_dem_grid(
            wc_data,
            wc_transform,
            wc_crs,
            dst_shape=slope_deg.shape,
            dst_transform=dem_transform,
            dst_crs=dem_crs,
        )

        # 4. Natural Earth coastline + waterbodies
        coast, water = load_coastline_and_waterbodies(bounds)

        # 5. Stable mask (in the DEM/slope UTM grid)
        stable_mask = build_stable_mask(
            wc_on_dem,
            slope_deg,
            coast,
            water,
            transform=dem_transform,
            crs=dem_crs,
            coast_buffer_m=5000.0,
            water_buffer_m=500.0,
            slope_max_deg=10.0,
        )
        stable_mask_class60_count = int((wc_on_dem == 60).sum())
        stable_mask_slope_ok_count = int(np.isfinite(slope_deg).sum())
        stable_mask_no_buffers = build_stable_mask(
            wc_on_dem,
            slope_deg,
            transform=dem_transform,
            crs=dem_crs,
            slope_max_deg=10.0,
        )
        stable_mask_coast_only = build_stable_mask(
            wc_on_dem,
            slope_deg,
            coast,
            None,
            transform=dem_transform,
            crs=dem_crs,
            coast_buffer_m=5000.0,
            slope_max_deg=10.0,
        )
        stable_mask_diagnostics: dict[str, object] = {
            "stable_mask_class60_count": stable_mask_class60_count,
            "stable_mask_slope_ok_count": stable_mask_slope_ok_count,
            "stable_mask_coast_excluded_count": int(
                stable_mask_no_buffers.sum() - stable_mask_coast_only.sum()
            ),
            "stable_mask_water_excluded_count": int(
                stable_mask_coast_only.sum() - stable_mask.sum()
            ),
            "stable_mask_final_count": int(stable_mask.sum()),
            "stable_mask_retention_pct": float(
                int(stable_mask.sum()) / max(stable_mask_class60_count, 1)
            ),
            "stable_mask_buffer_crs": str(dem_crs),
        }
        n_stable = int(stable_mask.sum())
        if n_stable < 1000:
            raise RuntimeError(
                f"{cfg.aoi_name}: stable_mask has only {n_stable} pixels; "
                "< 1000 minimum (AOI too small or contaminated)"
            )
        logger.info("{}: stable_mask n_stable={}", cfg.aoi_name, n_stable)

        # 5. Per-epoch: download SAFE, orbit, run CSLC
        burst_out = CACHE / "output" / cfg.aoi_name
        burst_out.mkdir(parents=True, exist_ok=True)
        opera_frame_search: dict[str, str | int | float | bool | None] | None = None
        # compass writes nested <burst_id>/<YYYYMMDD>/<burst_id>_<YYYYMMDD>.h5,
        # so ensure_resume_safe's top-level iterdir check can't see them.
        # Count recursively instead; skip the loop only when every epoch wrote.
        have_all_epochs = (
            len(list(burst_out.rglob("*.h5"))) >= len(cfg.sensing_window)
        )
        if not have_all_epochs:
            for epoch_idx, epoch in enumerate(cfg.sensing_window):
                granule_hint = _safe_granule_for_epoch(cfg.burst_id, epoch)
                safe = find_cached_safe(granule_hint, list(cfg.cached_safe_search_dirs))
                if safe is None:
                    safe = _download_safe_for_epoch(cfg.burst_id, epoch, CACHE / "input")
                elif not validate_safe_path(safe):
                    logger.warning("Ignoring invalid cached SAFE hit {}", safe)
                    safe = _download_safe_for_epoch(cfg.burst_id, epoch, CACHE / "input")
                orbit = fetch_orbit(
                    sensing_time=epoch,
                    satellite="S1A",
                    output_dir=CACHE / "orbits",
                )

                # D-07/D-09 amplitude sanity: download OPERA reference for first
                # epoch only, gated on cfg.run_amplitude_sanity (NOT a hard-coded
                # aoi_name check), and preserve OPERA frame-search evidence.
                if epoch_idx == 0 and cfg.run_amplitude_sanity:
                    _, opera_frame_search = _ensure_opera_reference_for_first_epoch(cfg)

                # run_cslc calls _mp.configure_multiprocessing() at its top (Phase 1 D-14)
                run_cslc(
                    safe_paths=[safe],
                    orbit_path=orbit,
                    dem_path=dem_path,
                    burst_ids=[cfg.burst_id],
                    output_dir=burst_out,
                    burst_database_file=_ensure_opera_burst_db(),
                )

        # 6. IFG coherence stack
        # compass writes outputs nested as <burst_out>/<burst_id>/<YYYYMMDD>/
        # <burst_id>_<YYYYMMDD>.h5, so use a recursive glob not a flat one.
        sorted_h5 = sorted(burst_out.rglob("*.h5"))
        ifgrams_stack = compute_ifg_coherence_stack(sorted_h5, boxcar_px=5)

        # Reproject stable_mask (DEM grid, ~30m) onto the CSLC output grid
        # (OPERA 5m range × 10m azimuth per runconfig) so that coherence_stats
        # + residual_mean_velocity can boolean-index the coherence stack.
        import h5py  # noqa: PLC0415
        from affine import Affine  # noqa: PLC0415
        from rasterio.warp import Resampling, reproject  # noqa: PLC0415

        with h5py.File(sorted_h5[0], "r") as _f:
            _xc = _f["/data/x_coordinates"][:]
            _yc = _f["/data/y_coordinates"][:]
            _xs = float(_f["/data/x_spacing"][()])
            _ys = float(_f["/data/y_spacing"][()])
            _epsg = int(_f["/data/projection"][()])
        cslc_transform = Affine(_xs, 0, _xc[0] - _xs / 2, 0, _ys, _yc[0] - _ys / 2)
        cslc_crs = f"EPSG:{_epsg}"
        cslc_shape = (ifgrams_stack.shape[-2], ifgrams_stack.shape[-1])
        stable_mask_cslc = np.zeros(cslc_shape, dtype=np.uint8)
        reproject(
            source=stable_mask.astype(np.uint8),
            destination=stable_mask_cslc,
            src_transform=dem_transform,
            src_crs=dem_crs,
            dst_transform=cslc_transform,
            dst_crs=cslc_crs,
            resampling=Resampling.nearest,
        )
        stable_mask_cslc = stable_mask_cslc.astype(bool)
        n_stable_on_cslc = int(stable_mask_cslc.sum())
        logger.info(
            "{}: reprojected stable_mask onto CSLC grid "
            "(DEM shape {} → CSLC shape {}); n_stable_on_cslc={}",
            cfg.aoi_name, stable_mask.shape, cslc_shape, n_stable_on_cslc,
        )

        # Intersect with CSLC valid-data mask. The CSLC output is a rectangular
        # grid, but the burst footprint is a parallelogram — ~64% of the grid
        # (for SoCal t144_308029_iw1) is NaN/zero outside the footprint.
        # Coherence is structurally 0 on those pixels, so leaving them in the
        # stable mask drags per-pixel-mean coherence to 0.0. Derive validity
        # from the coherence stack itself (pixels with any non-zero coherence
        # must have valid SLC data); avoids re-reading the h5.
        valid_on_cslc = (ifgrams_stack > 0).any(axis=0)
        stable_mask_cslc = stable_mask_cslc & valid_on_cslc
        n_stable_valid = int(stable_mask_cslc.sum())
        logger.info(
            "{}: intersected stable_mask with CSLC valid-data: "
            "{} → {} pixels ({} dropped as NaN/zero burst corners)",
            cfg.aoi_name, n_stable_on_cslc, n_stable_valid,
            n_stable_on_cslc - n_stable_valid,
        )
        if n_stable_valid < 100:
            raise RuntimeError(
                f"{cfg.aoi_name}: stable_mask_cslc has only {n_stable_valid} "
                f"valid pixels after burst-footprint intersection "
                f"(was {n_stable_on_cslc} before); AOI too sparse or "
                f"stable-terrain criteria too strict for this burst"
            )

        coh_stats = coherence_stats(
            ifgrams_stack, stable_mask_cslc, coherence_threshold=0.6
        )

        # 7. Residual velocity (linear-fit per D-Claude's-Discretion; P2.3)
        velocity_raster = compute_residual_velocity(
            sorted_h5, stable_mask_cslc, sensing_dates=list(cfg.sensing_window)
        )
        # Reference-frame alignment via stable-set median anchor (P2.3 mitigation)
        residual = residual_mean_velocity(
            velocity_raster, stable_mask_cslc, frame_anchor="median"
        )

        # 8. Amplitude sanity — gated on per-AOI run_amplitude_sanity flag (D-07).
        # BLOCKER 4 fix: flag drives whether compare_cslc runs; the EU script
        # (Plan 03-04) flips this to True on IberianAOI without editing the
        # conditional text.
        ra_result: ReferenceAgreementResultJson | None = None
        amplitude_blocker: CSLCBlockerEvidence | None = None
        if cfg.run_amplitude_sanity:
            if opera_frame_search is None:
                _, opera_frame_search = _ensure_opera_reference_for_first_epoch(cfg)
            ref_aoi_dir = CACHE / "opera_reference" / cfg.aoi_name
            ref_h5_list = sorted(ref_aoi_dir.glob("*.h5"))
            if ref_h5_list:
                opera_ref_h5 = ref_h5_list[0]
                product_h5 = sorted_h5[0]
                cmp_result = compare_cslc(
                    product_path=product_h5,
                    reference_path=opera_ref_h5,
                )
                ra = cmp_result.reference_agreement
                # compare_cslc stores the amplitude-correlation as
                # 'amplitude_r' (not 'amplitude_correlation'); the -1.0
                # sentinel appeared in metrics.json because the old key
                # lookup always fell through to the default.
                ra_result = ReferenceAgreementResultJson(
                    measurements={
                        "amp_r": float(ra.measurements.get("amplitude_r", -1.0)),
                        "amp_rmse_db": float(ra.measurements.get("amplitude_rmse_db", -1.0)),
                    },
                    criterion_ids=["cslc.amplitude_r_min", "cslc.amplitude_rmse_db_max"],
                )
            else:
                if cfg.aoi_name.startswith("Mojave/"):
                    amplitude_blocker = CSLCBlockerEvidence(
                        reason_code="mojave_opera_frame_unavailable",
                        evidence={"opera_frame_search": opera_frame_search or {}},
                    )
                logger.warning(
                    "{}: run_amplitude_sanity=True but no OPERA ref h5 in {}; "
                    "recording candidate BINDING blocker if this is a Mojave fallback",
                    cfg.aoi_name, ref_aoi_dir,
                )

        # 9. Stable-mask sanity artifacts (P2.1) — use the CSLC-grid stable_mask
        # (same grid as coherence_stack so _write_sanity_artifacts can boolean-
        # index into the coherence stack without another shape mismatch).
        _write_sanity_artifacts(
            cfg.aoi_name,
            stable_mask=stable_mask_cslc,
            coherence_stack=ifgrams_stack,
            transform=cslc_transform,
            crs=cslc_crs,
            out_dir=CACHE / "sanity" / cfg.aoi_name,
            stable_mask_diagnostics=stable_mask_diagnostics,
        )

        # 10. Build AOIResult -- CALIBRATING per D-03 first-rollout
        # PASS/FAIL is intentionally NOT emitted regardless of measured numbers.
        pq = ProductQualityResultJson(
            measurements={
                "coherence_median_of_persistent": coh_stats["median_of_persistent"],
                "residual_mm_yr": residual,
                # Diagnostics (not gate-critical; surfaced in CONCLUSIONS §4b)
                "coherence_mean": coh_stats["mean"],
                "coherence_median": coh_stats["median"],
                "coherence_p25": coh_stats["p25"],
                "coherence_p75": coh_stats["p75"],
                "persistently_coherent_fraction": coh_stats["persistently_coherent_fraction"],
            },
            criterion_ids=[
                "cslc.selfconsistency.coherence_min",
                "cslc.selfconsistency.residual_mm_yr_max",
            ],
        )
        candidate_binding = _candidate_binding_for_pq(pq)
        if amplitude_blocker is not None and cfg.aoi_name.startswith("Mojave/"):
            candidate_binding = CSLCCandidateBindingResult(
                verdict="BINDING BLOCKER",
                thresholds=CSLCCandidateThresholds(
                    coherence_median_of_persistent_min=CANDIDATE_COHERENCE_MIN,
                    residual_mm_yr_abs_max=CANDIDATE_RESIDUAL_ABS_MAX_MM_YR,
                ),
                blocker=amplitude_blocker,
            )

        return AOIResult(
            aoi_name=cfg.aoi_name,
            regime=cfg.regime,
            burst_id=cfg.burst_id,
            sensing_window=[e.isoformat() for e in cfg.sensing_window],
            status="CALIBRATING",    # D-03 first-rollout -- never PASS/FAIL in Phase 3
            stable_mask_pixels=n_stable,
            product_quality=pq,
            reference_agreement=ra_result,
            candidate_binding=candidate_binding,
            opera_frame_search=opera_frame_search,
        )

    # -- Main loop -----------------------------------------------------------

    per_aoi: list[AOIResult] = []
    per_aoi_input_hashes: dict[str, dict[str, str]] = {}
    for cfg in AOIS:
        t0 = time.time()
        try:
            row = process_aoi(cfg)
            per_aoi.append(row)
            per_aoi_input_hashes[cfg.aoi_name] = _collect_input_hashes(cfg)
            logger.info(
                "AOI {} {} in {:.0f}s", cfg.aoi_name, row.status, time.time() - t0
            )
        except Exception as e:  # noqa: BLE001 - per-AOI isolation (D-06 analog)
            tb = traceback.format_exc()
            logger.error(
                "AOI {} FAIL ({:.0f}s): {}", cfg.aoi_name, time.time() - t0, e
            )
            per_aoi.append(AOIResult(
                aoi_name=cfg.aoi_name,
                regime=cfg.regime,
                burst_id=cfg.burst_id or None,
                status="FAIL",
                candidate_binding=CSLCCandidateBindingResult(
                    verdict="BINDING BLOCKER",
                    thresholds=CSLCCandidateThresholds(),
                    blocker=CSLCBlockerEvidence(
                        reason_code="aoi_processing_failed",
                        evidence={"error": repr(e)},
                    ),
                ),
                error=repr(e),
                traceback=tb,
            ))

    # -- Aggregate + write metrics.json --------------------------------------

    pass_count = sum(1 for r in per_aoi if r.status in ("PASS", "CALIBRATING"))
    total = len(per_aoi)
    any_blocker = any(r.status == "BLOCKER" for r in per_aoi)
    cell_status = _resolve_cell_status(per_aoi)

    pq_agg = _worst_pq(per_aoi)
    ra_agg = _worst_ra(per_aoi)

    metrics = CSLCSelfConsistNAMCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(measurements={}, criterion_ids=[]),
        criterion_ids_applied=[
            "cslc.selfconsistency.coherence_min",
            "cslc.selfconsistency.residual_mm_yr_max",
            "cslc.amplitude_r_min",
            "cslc.amplitude_rmse_db_max",
        ],
        pass_count=pass_count,
        total=total,
        cell_status=cell_status,
        any_blocker=any_blocker,
        product_quality_aggregate=pq_agg,
        reference_agreement_aggregate=ra_agg,
        per_aoi=per_aoi,
        candidate_binding=_candidate_binding_for_rows(per_aoi),
    )

    metrics_path = CACHE / "metrics.json"
    metrics_path.write_text(metrics.model_dump_json(indent=2))
    logger.info("Wrote {}", metrics_path)

    # -- meta.json -----------------------------------------------------------

    git_sha, git_dirty = get_git_sha()
    flat_input_hashes: dict[str, str] = {}
    for _aoi_name, kv in per_aoi_input_hashes.items():
        flat_input_hashes.update(kv)

    meta = MetaJson(
        schema_version=1,
        git_sha=git_sha,
        git_dirty=git_dirty,
        run_started_iso=run_started_iso,
        run_duration_s=time.time() - run_started,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        input_hashes=flat_input_hashes,
    )
    meta_path = CACHE / "meta.json"
    meta_path.write_text(meta.model_dump_json(indent=2))
    logger.info("Wrote {}", meta_path)

    # -- Summary banner (PATTERNS "Summary banner at end of run") ------------

    print()
    print("=" * 70)
    print(
        f"eval-cslc-selfconsist-nam: {pass_count}/{total} {cell_status}",
        ("[investigation]" if any_blocker else ""),
    )
    for row in per_aoi:
        coh = (
            row.product_quality.measurements.get("coherence_median_of_persistent", -1.0)
            if row.product_quality
            else -1.0
        )
        res = (
            row.product_quality.measurements.get("residual_mm_yr", -1.0)
            if row.product_quality
            else -1.0
        )
        print(
            f"  [{row.status}] {row.aoi_name:20s} "
            f"coh={coh:.3f} residual={res:+.2f} mm/yr"
        )
    print("=" * 70)

    # Exit code contract (D-03 first-rollout):
    #   CALIBRATING -> 0 (success; calibration data collected)
    #   MIXED       -> 0 (partial success; BLOCKER surfaces via matrix_writer)
    #   PASS        -> 0 (post-BINDING, future)
    #   BLOCKER     -> 1 (all AOIs blocked; no data collected)
    #   FAIL        -> 1 (hard failures; investigate)
    sys.exit(0 if cell_status in ("PASS", "CALIBRATING", "MIXED") else 1)
