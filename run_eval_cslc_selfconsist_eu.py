# run_eval_cslc_selfconsist_eu.py -- EU CSLC-S1 self-consistency + EGMS L2a
#
# Phase 3 (v1.1) deliverable — CSLC-05 three-number schema on Iberian Meseta:
#   (a) OPERA CSLC amplitude sanity (r > 0.6, RMSE < 4 dB) — BINDING reference-agreement
#   (b) Self-consistency coherence median_of_persistent > 0.7 — CALIBRATING product-quality
#   (c) Self-consistency + EGMS L2a stable-PS residual < 5 mm/yr — CALIBRATING product-quality
#
# ENV-07 discipline: structurally identical to run_eval_cslc_selfconsist_nam.py
# except for AOIS literal, EGMS L2a download step, and CACHE path prefix.
# All helpers are byte-identical copy-paste — see PATTERNS §ENV-07 rule.
#
# Orchestration:
#   - Declarative AOIS: list[AOIConfig] = [IberianAOI] (D-05)
#   - IberianAOI runs as the executable primary path; Phase 8 artifact names
#     Ebro Basin and La Mancha as acquisition-backed EU fallback AOIs pending
#     burst-id derivation before they are wired into fallback_chain
#   - Per-AOI try/except isolation (D-06)
#   - Per-burst whole-pipeline skip + per-stage ensure_resume_safe (D-08)
#   - Cached-SAFE reuse via harness.find_cached_safe (D-02)
#   - EU-only: EGMS L2a stable-PS residual step (_fetch_egms_l2a + compare_cslc_egms_l2a_residual)
#   - Single eval-cslc-selfconsist-eu/metrics.json (CSLCSelfConsistEUCellMetrics)
#
# Makefile target: `make eval-cslc-eu` -> supervisor wraps this script.
#   EXPECTED_WALL_S = 14h covers Iberian 15-epoch stack + 2-candidate fallback
#   worst-case + EGMStoolkit L2a download + per-stage ensure_resume_safe + 2x margin.
#   Warm re-run: <= 5 min (all CSLCs + EGMS CSVs cached).
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

# Iberian 15-epoch SoCal-style stack + EGMStoolkit L2a download + per-stage
# ensure_resume_safe + supervisor margin. Warm re-run <= 5 min.
EXPECTED_WALL_S = 60 * 60 * 14   # 50400s (CONTEXT D-Claude's-Discretion EU budget)
CANDIDATE_COHERENCE_MIN = 0.75
CANDIDATE_RESIDUAL_ABS_MAX_MM_YR = 2.0
CANDIDATE_EGMS_RESIDUAL_ABS_MAX_MM_YR = 5.0


if __name__ == "__main__":
    import hashlib
    import json  # noqa: F401  -- reserved for future provenance extensions
    import math
    import os
    import platform
    import subprocess
    import sys
    import time
    import traceback
    from dataclasses import dataclass
    from datetime import datetime, timedelta
    from pathlib import Path

    import earthaccess
    import numpy as np
    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.data.dem import fetch_dem
    from subsideo.data.natural_earth import load_coastline_and_waterbodies
    from subsideo.data.orbits import fetch_orbit
    from subsideo.data.worldcover import fetch_worldcover_class60, load_worldcover_for_bbox
    from subsideo.products.cslc import run_cslc
    from subsideo.validation.compare_cslc import (
        compare_cslc,
        compare_cslc_egms_l2a_residual_diagnostics,
    )
    from subsideo.validation.criteria import CRITERIA  # noqa: F401
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
        CSLCSelfConsistEUCellMetrics,
        MetaJson,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
    )
    from subsideo.validation.selfconsistency import (
        coherence_stats,
        compute_residual_velocity,
        residual_mean_velocity,
    )
    from subsideo.validation.stable_terrain import build_stable_mask

    load_dotenv()

    credential_preflight([
        "EARTHDATA_USERNAME",
        "EARTHDATA_PASSWORD",
    ])
    # CDSE creds required for fresh EU SAFE downloads; not all bursts need
    # CDSE when cached reuses hit (D-02). Accept runtime error per-AOI.

    # -- Configuration ----------------------------------------------------

    @dataclass(frozen=True)
    class AOIConfig:
        """Per-AOI declarative config for run_eval_cslc_selfconsist_eu.AOIS (D-05)."""

        aoi_name: str                          # "Iberian" or a future artifact-backed fallback
        regime: str                            # e.g. "iberian-meseta-sparse-vegetation"
        burst_id: str                          # JPL lowercase; "" for parent rows
        sensing_window: tuple                  # tuple[datetime, ...] -- 15 entries per leaf
        output_epsg: int                       # UTM zone
        centroid_lat: float
        cached_safe_search_dirs: tuple         # tuple[Path, ...]
        fallback_chain: tuple = ()             # tuple[AOIConfig, ...]; empty for leaves
        # BLOCKER 4 fix: per-AOI attribute driving amplitude-sanity gating.
        # IberianAOI + EU fallbacks = True (D-07 runs compare_cslc on first epoch).
        # The leaf-path conditional consults cfg.run_amplitude_sanity -- not cfg.aoi_name
        # -- so the EU fork sets True on all Iberian AOIs without editing the conditional.
        run_amplitude_sanity: bool = False

    # AOIS -- refreshed against
    # .planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md.

    # BLOCKER 3 cross-reference: the primary epoch tuple is sourced from the
    # refreshed artifact's `### Iberian Meseta-North` section. The artifact also
    # accepts Ebro Basin and La Mancha as EU fallback AOIs, but their burst IDs
    # must be derived from the EU burst DB before they can be safely wired here.
    # The IBERIAN_EPOCHS alias below (= IBERIAN_PRIMARY_EPOCHS) is kept for readability.
    # 15-epoch Meseta-North sensing window for burst t103_219329_iw1.
    # Verified via ASF search on 2026-04-24 (the 03-02 probe emitted multi-
    # track fabricated dates with mixed 06:18/06:26/18:11 pass times; a
    # single S1A burst has a single consistent UTC pass). All S1A POEORB,
    # 12-day cadence, covers 168 days. Pass time 18:03:20 UTC (track 103
    # descending over Iberian Meseta).
    IBERIAN_PRIMARY_EPOCHS: tuple[datetime, ...] = (
        datetime(2024, 1, 5, 18, 3, 21),
        datetime(2024, 1, 17, 18, 3, 20),
        datetime(2024, 1, 29, 18, 3, 20),
        datetime(2024, 2, 10, 18, 3, 19),
        datetime(2024, 2, 22, 18, 3, 19),
        datetime(2024, 3, 5, 18, 3, 19),
        datetime(2024, 3, 17, 18, 3, 20),
        datetime(2024, 3, 29, 18, 3, 20),
        datetime(2024, 4, 10, 18, 3, 19),
        datetime(2024, 4, 22, 18, 3, 20),
        datetime(2024, 5, 4, 18, 3, 21),
        datetime(2024, 5, 16, 18, 3, 21),
        datetime(2024, 5, 28, 18, 3, 20),
        datetime(2024, 6, 9, 18, 3, 20),
        datetime(2024, 6, 21, 18, 3, 19),
    )

    # Alias for the primary burst (used in IberianAOI below). Each fallback binds
    # its own per-AOI window once future work derives safe EU burst IDs.
    IBERIAN_EPOCHS = IBERIAN_PRIMARY_EPOCHS

    # Minimum-viable EU path (03-04 Task 2): only the Meseta-North primary
    # runs. Phase 8 rejected the stale Alentejo and Massif Central v1.1 rows
    # and accepted Ebro Basin + La Mancha as acquisition-backed fallback AOIs,
    # but those rows still need EU burst DB derivation before use. The
    # fallback_chain=() below keeps IberianAOI as a leaf with the real
    # Meseta-North burst t103_219329_iw1 (EPSG 32630).
    IberianAOI = AOIConfig(
        aoi_name="Iberian",
        regime="iberian-meseta-sparse-vegetation",
        burst_id="t103_219329_iw1",   # Meseta-North primary — Phase 2 carry-forward
        sensing_window=IBERIAN_EPOCHS,
        output_epsg=32630,
        centroid_lat=41.05,
        cached_safe_search_dirs=(
            Path("eval-cslc-selfconsist-eu/input"),
            Path("eval-rtc-eu/input"),   # D-02: reuse from Phase 2 RTC-EU eval
        ),
        fallback_chain=(),
        run_amplitude_sanity=True,   # BLOCKER 4 fix: EU primary runs D-07 amplitude sanity
    )

    AOIS: list[AOIConfig] = [IberianAOI]

    CACHE = Path("eval-cslc-selfconsist-eu")
    for sub in ("input", "output", "opera_reference", "dem", "orbits",
                "worldcover", "coastline", "sanity", "egms"):
        (CACHE / sub).mkdir(parents=True, exist_ok=True)

    # compass needs a real burst_database_file path. The OPERA burst DB
    # (opera-adt/burst_db v0.9.0 opera-burst-bbox-only.sqlite3) covers all
    # global S1 bursts including the EU — t103_219329_iw1 Meseta-North has
    # an entry there (EPSG 32630). Phase 1's planned eu_burst_db.sqlite
    # doesn't exist yet, so reuse the OPERA DB the NAM script auto-fetches
    # (cached at ~/.subsideo/opera_burst_bbox.sqlite3).
    EU_BURST_DB_PATH = Path.home() / ".subsideo" / "opera_burst_bbox.sqlite3"
    if not EU_BURST_DB_PATH.exists():
        raise RuntimeError(
            f"OPERA burst DB missing at {EU_BURST_DB_PATH}; "
            f"run `make eval-cslc-nam` once to trigger auto-fetch, "
            f"or fetch manually from "
            f"https://github.com/opera-adt/burst_db/releases/download/"
            f"v0.9.0/opera-burst-bbox-only.sqlite3.zip"
        )

    run_started = time.time()
    run_started_iso = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%SZ")

    auth = earthaccess.login(strategy="environment")  # noqa: F841

    # -- Helpers ---------------------------------------------------------

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
        """Construct a search-friendly granule ID pattern for a burst + epoch."""
        # Sentinel-1 SAFE naming convention: S1A_IW_SLC__... with date YYYYMMDD
        return f"S1A_IW_SLC__{epoch.strftime('%Y%m%d')}*"

    def _download_safe_for_epoch(burst_id: str, epoch: datetime, dest_dir: Path) -> Path:
        """Download Sentinel-1 SAFE for a burst epoch from ASF.

        Mirrors the NAM script: filters ASF search by relativeOrbit (parsed
        from burst_id) + the burst footprint polygon so we don't accidentally
        grab a different orbit acquiring at the same UTC minute. Validates
        the zip before returning; corrupt partial downloads are deleted +
        re-raised. CDSE STAC returned 0 items for 2024 Iberian queries,
        ASF serves the same S1 SLCs reliably.
        """
        import asf_search as asf  # noqa: PLC0415
        from shapely.geometry import box as _shapely_box  # noqa: PLC0415

        dest_dir.mkdir(parents=True, exist_ok=True)

        track_num = int(burst_id.split("_")[0].lstrip("t"))
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

        # S1 IW SLCs are cut into ~25s slices per pass, and the ±10 min
        # search window routinely matches 2+ slices per orbit. Pick the
        # slice whose (startTime, stopTime) contains the target epoch —
        # compass needs THE slice that holds the burst, not just one from
        # the same orbit (which would fail at runconfig.correlate_burst_to_orbit
        # with "Could not find any of the burst IDs in the provided safe files").
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

    def _compute_ifg_coherence_stack(
        hdf5_paths: list[Path],
        *,
        boxcar_px: int = 5,
    ) -> np.ndarray:
        """Form sequential IFGs + compute coherence via boxcar window.

        Per PATTERNS FEATURES Phase 2 line 59: form 14 sequential IFGs
        via ``prod_t * conj(prod_t+1)``, compute pixel-wise coherence via
        small boxcar (5x5), return (N, H, W) float coherence stack.
        """
        import h5py  # noqa: PLC0415
        from scipy.ndimage import uniform_filter  # noqa: PLC0415

        stacks = []
        for p in hdf5_paths:
            with h5py.File(p, "r") as f:
                for dset_path in ("/data/VV", "/data/HH",
                                  "/science/SENTINEL1/CSLC/grids/VV",
                                  "/science/SENTINEL1/CSLC/grids/HH"):
                    if dset_path in f:
                        arr = f[dset_path][:].astype("complex64")
                        # Rectangular CSLC grid is NaN outside the burst
                        # parallelogram footprint; NaN poisons uniform_filter
                        # and forces coh == 0 everywhere. Zero-fill so the
                        # filter averages with 0s at the burst boundary.
                        bad = ~(np.isfinite(arr.real) & np.isfinite(arr.imag))
                        if bad.any():
                            arr = arr.copy()
                            arr[bad] = np.complex64(0)
                        stacks.append(arr)
                        break

        coherence_stack = []
        for i in range(len(stacks) - 1):
            ifg = stacks[i] * np.conj(stacks[i + 1])
            # Coherence estimate: |E[ifg]| / sqrt(E[|a|^2] * E[|b|^2])
            num = np.abs(
                uniform_filter(ifg.real, size=boxcar_px)
                + 1j * uniform_filter(ifg.imag, size=boxcar_px)
            ).astype("float32")
            denom_a = uniform_filter(np.abs(stacks[i]) ** 2, size=boxcar_px)
            denom_b = uniform_filter(np.abs(stacks[i + 1]) ** 2, size=boxcar_px)
            denom = np.sqrt(denom_a * denom_b + 1e-12).astype("float32")
            coh = np.clip(num / denom, 0.0, 1.0)
            coherence_stack.append(coh)

        return np.stack(coherence_stack, axis=0)  # (N-1, H, W)

    def _compute_slope_deg(dem_path: Path) -> tuple[np.ndarray, object, object]:
        """Compute slope in degrees from a DEM GeoTIFF via numpy.gradient.

        Returns (slope_deg, transform, crs) so the caller can reproject other
        rasters (WorldCover) onto this grid before feeding build_stable_mask.
        """
        import rasterio  # noqa: PLC0415

        with rasterio.open(dem_path) as src:
            dem = src.read(1).astype("float32")
            res_x = abs(src.transform.a)
            res_y = abs(src.transform.e)
            dem_transform = src.transform
            dem_crs = src.crs

        dzdx = np.gradient(dem, res_x, axis=1)
        dzdy = np.gradient(dem, res_y, axis=0)
        slope_deg = np.degrees(np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2))).astype("float32")
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
        """Reproject WorldCover onto the DEM grid (nearest neighbour — class labels)."""
        import rasterio  # noqa: PLC0415, F401
        from rasterio.warp import Resampling, reproject  # noqa: PLC0415

        dst = np.zeros(dst_shape, dtype=wc_data.dtype)
        reproject(
            source=wc_data,
            destination=dst,
            src_transform=wc_transform,
            src_crs=wc_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )
        return dst

    def _write_sanity_artifacts(
        aoi_name: str,
        *,
        stable_mask: np.ndarray,
        coherence_stack: np.ndarray,
        transform: object,
        crs: object,
        out_dir: Path,
        stable_mask_diagnostics: dict[str, object] | None = None,
    ) -> None:
        """Emit P2.1 stable-mask sanity artifacts for one AOI.

        Writes:
          - coherence_histogram.png  -- histogram of per-pixel mean coherence
            over stable mask + red vertical line at 0.7 gate threshold.
          - stable_mask_over_basemap.png  -- stable mask overlaid on crude basemap.
          - mask_metadata.json  -- JSON with n_stable_pixels, bounding_box, regime.
        """
        import json as _json  # noqa: PLC0415

        import matplotlib  # noqa: PLC0415
        import matplotlib.pyplot as plt  # noqa: PLC0415

        matplotlib.use("Agg")

        out_dir.mkdir(parents=True, exist_ok=True)
        n_stable = int(stable_mask.sum())

        # Per-pixel mean coherence over the stack
        per_pixel_mean = coherence_stack.mean(axis=0)
        vals = per_pixel_mean[stable_mask]

        # Coherence histogram
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(vals, bins=50, color="steelblue", edgecolor="white", alpha=0.8)
        ax.axvline(0.7, color="red", linestyle="--", linewidth=1.5, label="gate=0.7")
        ax.set_xlabel("Per-pixel mean coherence")
        ax.set_ylabel("Count")
        ax.set_title(f"Coherence distribution -- {aoi_name} stable mask (n={n_stable})")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / "coherence_histogram.png", dpi=150)
        plt.close(fig)

        # Stable mask over basemap (simple boolean image)
        fig2, ax2 = plt.subplots(figsize=(8, 8))
        ax2.imshow(stable_mask.astype("float32"), cmap="Greens", vmin=0, vmax=1,
                   origin="upper")
        ax2.set_title(f"Stable mask -- {aoi_name}\n(green=stable, white=excluded)")
        ax2.axis("off")
        fig2.tight_layout()
        fig2.savefig(out_dir / "stable_mask_over_basemap.png", dpi=150)
        plt.close(fig2)

        # mask_metadata.json
        h, w = stable_mask.shape
        meta = {
            "n_stable_pixels": n_stable,
            "total_pixels": h * w,
            "stable_pct_of_aoi": round(n_stable / (h * w) * 100, 2),
            "aoi_name": aoi_name,
        }
        if stable_mask_diagnostics:
            meta.update(stable_mask_diagnostics)
        (out_dir / "mask_metadata.json").write_text(_json.dumps(meta, indent=2))

    def _fetch_egms_l2a(
        bbox: tuple[float, float, float, float],
        *,
        out_dir: Path,
    ) -> list[Path]:
        """Download EGMS L2a release 2019_2023 per-track CSVs covering bbox.

        Lazy-imports EGMStoolkit (pip-installed separately per CONTEXT Stack).
        Cache-hit path: if CSVs already present in out_dir, return them without
        re-downloading (D-08 resume-safe pattern for the EGMS download step).
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        cached = sorted(out_dir.glob("*.csv"))
        if cached:
            logger.info("EGMS L2a cache hit: {} CSVs in {}", len(cached), out_dir)
            return cached
        try:
            import EGMStoolkit  # noqa: PLC0415
        except ImportError as e:
            raise ImportError(
                "EGMStoolkit 0.2.15 required for Phase 3 EU eval; "
                "install via `pip install EGMStoolkit==0.2.15`"
            ) from e
        west, south, east, north = bbox
        # Use product_level='L2a' (NOT Ortho); release='2019_2023' per BOOTSTRAP 2.3.
        EGMStoolkit.download(
            bbox=[west, south, east, north],
            product_level="L2a",
            release="2019_2023",
            output_dir=str(out_dir),
        )
        csvs = sorted(out_dir.glob("*.csv"))
        if not csvs:
            raise FileNotFoundError(f"No EGMS L2a CSVs found in {out_dir} after download")
        logger.info("EGMS L2a: downloaded {} per-track CSVs to {}", len(csvs), out_dir)
        return csvs

    def _write_velocity_geotiff(
        velocity: np.ndarray,
        transform: object,
        crs: object,
        *,
        out_path: Path,
    ) -> Path:
        """Serialise a (H, W) float32 velocity array to a GeoTIFF via rasterio."""
        import rasterio  # noqa: PLC0415

        out_path.parent.mkdir(parents=True, exist_ok=True)
        h, w = velocity.shape
        with rasterio.open(
            out_path, "w", driver="GTiff",
            height=h, width=w, count=1, dtype="float32",
            crs=crs, transform=transform, nodata=float("nan"),
            compress="DEFLATE", tiled=True, blockxsize=512, blockysize=512,
        ) as dst:
            dst.write(velocity.astype("float32"), 1)
        return out_path

    def _collect_input_hashes(cfg: AOIConfig) -> dict[str, str]:
        """Hash primary inputs for meta.json provenance."""
        hashes: dict[str, str] = {}
        # Hash DEM
        dem_dir = CACHE / "dem"
        for dem_file in sorted(dem_dir.glob("*.tif")):
            hashes[f"dem/{dem_file.name}"] = sha256_of_file(dem_file)
        # Hash orbit files
        orbit_dir = CACHE / "orbits"
        for orb in sorted(orbit_dir.glob("*.EOF")):
            hashes[f"orbit/{orb.name}"] = sha256_of_file(orb)
        # Hash OPERA reference HDF5 (first epoch only, amplitude sanity)
        if cfg.run_amplitude_sanity:
            ref_dir = CACHE / "opera_reference" / cfg.aoi_name
            for ref_h5 in sorted(ref_dir.glob("*.h5")):
                hashes[f"opera_ref/{ref_h5.name}"] = sha256_of_file(ref_h5)
        # Hash EGMS CSVs
        egms_dir = CACHE / "egms" / cfg.aoi_name
        for csv_file in sorted(egms_dir.glob("*.csv")):
            hashes[f"egms/{csv_file.name}"] = sha256_of_file(csv_file)
        return hashes

    def _opera_burst_upper(burst_id: str) -> str:
        """Convert JPL lowercase burst ID to OPERA granule burst token."""
        parts = burst_id.split("_")
        return f"T{parts[0][1:]}-{parts[1]}-{parts[2].upper()}"

    def _ensure_opera_reference_for_first_epoch(cfg: AOIConfig) -> list[Path]:
        """Ensure first-epoch OPERA reference search runs even on warm CSLC caches."""
        epoch = cfg.sensing_window[0]
        ref_aoi_dir = CACHE / "opera_reference" / cfg.aoi_name
        ref_aoi_dir.mkdir(parents=True, exist_ok=True)
        ref_h5_candidates = sorted(ref_aoi_dir.glob("*.h5"))
        if ref_h5_candidates:
            return ref_h5_candidates

        ref_results = earthaccess.search_data(
            short_name="OPERA_L2_CSLC-S1_V1",
            temporal=(epoch - timedelta(hours=1), epoch + timedelta(hours=1)),
            granule_name=f"OPERA_L2_CSLC-S1_{_opera_burst_upper(cfg.burst_id)}*",
        )
        if ref_results:
            ref_metadata = [
                {
                    "sensing_datetime": (
                        g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
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
        return ref_h5_candidates

    def _resolve_cell_status(rows: list[AOIResult]) -> str:
        """Aggregate per-AOI statuses into a single cell-level status.

        Returns a CSLCCellStatus literal: PASS | FAIL | CALIBRATING | MIXED | BLOCKER.
        Single-AOI EU variant; logic reused verbatim from NAM script.
        """
        statuses = {r.status for r in rows}
        if statuses == {"CALIBRATING"}:
            return "CALIBRATING"
        if "BLOCKER" in statuses and "CALIBRATING" in statuses:
            return "MIXED"
        if statuses == {"BLOCKER"}:
            return "BLOCKER"
        if "FAIL" in statuses:
            return "FAIL"
        if "PASS" in statuses and statuses <= {"PASS", "CALIBRATING"}:
            return "PASS" if statuses == {"PASS"} else "MIXED"
        return "FAIL"

    def _candidate_binding_for_pq(
        pq: ProductQualityResultJson | None,
        *,
        egms_l2a_blocker: CSLCBlockerEvidence | None = None,
        amplitude_blocker: CSLCBlockerEvidence | None = None,
    ) -> CSLCCandidateBindingResult:
        thresholds = CSLCCandidateThresholds(
            coherence_median_of_persistent_min=CANDIDATE_COHERENCE_MIN,
            residual_mm_yr_abs_max=CANDIDATE_RESIDUAL_ABS_MAX_MM_YR,
        )
        if pq is None:
            return CSLCCandidateBindingResult(verdict="BINDING BLOCKER", thresholds=thresholds)
        if amplitude_blocker is not None:
            return CSLCCandidateBindingResult(
                verdict="BINDING BLOCKER",
                thresholds=thresholds,
                blocker=amplitude_blocker,
            )
        measurements = pq.measurements
        if (
            egms_l2a_blocker is not None
            and "egms_l2a_stable_ps_residual_mm_yr" not in measurements
        ):
            return CSLCCandidateBindingResult(
                verdict="BINDING BLOCKER",
                thresholds=thresholds,
                blocker=egms_l2a_blocker,
            )
        coh = float(measurements.get("coherence_median_of_persistent", float("nan")))
        resid = abs(float(measurements.get("residual_mm_yr", float("nan"))))
        egms = abs(float(measurements.get("egms_l2a_stable_ps_residual_mm_yr", float("nan"))))
        verdict = (
            "BINDING PASS"
            if (
                np.isfinite(coh)
                and np.isfinite(resid)
                and np.isfinite(egms)
                and coh >= CANDIDATE_COHERENCE_MIN
                and resid <= CANDIDATE_RESIDUAL_ABS_MAX_MM_YR
                and egms <= CANDIDATE_EGMS_RESIDUAL_ABS_MAX_MM_YR
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
        """Worst-case product-quality aggregate across all AOIs."""
        best_coh = float("inf")
        worst_resid_abs = float("-inf")
        worst_resid = 0.0
        worst_aoi = ""
        for row in rows:
            if row.product_quality is None:
                continue
            m = row.product_quality.measurements
            coh = m.get("coherence_median_of_persistent", float("inf"))
            resid = m.get("residual_mm_yr", float("-inf"))
            if coh < best_coh:
                best_coh = coh
                worst_aoi = row.aoi_name
            resid_abs = abs(float(resid))
            if resid_abs > worst_resid_abs:
                worst_resid_abs = resid_abs
                worst_resid = float(resid)
        return {
            "worst_coherence_median_of_persistent": best_coh if best_coh != float("inf") else 0.0,
            "worst_residual_mm_yr": worst_resid if worst_resid_abs != float("-inf") else 0.0,
            "worst_aoi": worst_aoi,
        }

    def _worst_ra(rows: list[AOIResult]) -> dict[str, float | str]:
        """Worst-case reference-agreement aggregate across AOIs with amplitude sanity."""
        worst_r = float("inf")
        worst_rmse = float("-inf")
        worst_aoi = ""
        for row in rows:
            if row.reference_agreement is None:
                continue
            m = row.reference_agreement.measurements
            r = m.get("amplitude_r", float("inf"))
            rmse = m.get("amplitude_rmse_db", float("-inf"))
            if r < worst_r:
                worst_r = r
                worst_aoi = row.aoi_name
            if rmse > worst_rmse:
                worst_rmse = rmse
        return {
            "worst_amp_r": worst_r if worst_r != float("inf") else 0.0,
            "worst_amp_rmse_db": worst_rmse if worst_rmse != float("-inf") else 0.0,
            "worst_aoi": worst_aoi,
        }

    # -- Per-AOI pipeline ------------------------------------------------

    def process_aoi(cfg: AOIConfig) -> AOIResult:
        """Run the CSLC self-consistency pipeline for one AOI; return an AOIResult.

        Handles fallback_chain recursion at the top (Iberian parent -> Alentejo ->
        MassifCentral), then the leaf path for single-burst processing.
        """
        # Handle fallback-chain recursion (Iberian parent -> Alentejo -> MassifCentral)
        if cfg.fallback_chain:
            attempts: list[AOIResult] = []
            for idx, candidate in enumerate(cfg.fallback_chain, start=1):
                try:
                    child = process_aoi(candidate)  # leaf path; no further recursion
                    child = child.model_copy(update={"attempt_index": idx})
                    attempts.append(child)
                    if child.status in ("PASS", "CALIBRATING"):
                        logger.info(
                            "{} attempt #{}: {} -- {}",
                            cfg.aoi_name, idx, candidate.aoi_name, child.status,
                        )
                        break
                except Exception as e:  # noqa: BLE001
                    tb = traceback.format_exc()
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
            # Parent status: first CALIBRATING/PASS wins; all-FAIL -> BLOCKER.
            first_success = next(
                (a for a in attempts if a.status in ("PASS", "CALIBRATING")), None
            )
            if first_success is not None:
                parent_status = first_success.status
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
                reason=None if first_success else (
                    f"All {len(cfg.fallback_chain)} fallbacks FAILed"
                ),
            )

        # Leaf path: single-AOI processing
        logger.info("Processing leaf AOI {} (burst {})", cfg.aoi_name, cfg.burst_id)
        bounds = bounds_for_burst(cfg.burst_id, buffer_deg=0.5)

        # 1. WorldCover
        wc_tiles = fetch_worldcover_class60(bounds, out_dir=CACHE / "worldcover")
        wc_data, wc_transform, wc_crs = load_worldcover_for_bbox(
            bounds, tiles_dir=wc_tiles
        )

        # 2. DEM + slope (fetch_dem requires output_epsg and returns a tuple)
        dem_aoi_dir = CACHE / "dem" / cfg.aoi_name
        dem_tifs = sorted(dem_aoi_dir.glob("*.tif")) if dem_aoi_dir.exists() else []
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
            wc_data, wc_transform, wc_crs,
            dst_shape=slope_deg.shape,
            dst_transform=dem_transform,
            dst_crs=dem_crs,
        )

        # 4. Natural Earth coastline + waterbodies
        coast, water = load_coastline_and_waterbodies(bounds)

        # 5. Stable mask (in the DEM/slope UTM grid)
        stable_mask = build_stable_mask(
            wc_on_dem, slope_deg, coast, water,
            transform=dem_transform, crs=dem_crs,
            coast_buffer_m=5000.0, water_buffer_m=500.0, slope_max_deg=10.0,
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
                f"{cfg.aoi_name}: stable_mask has only {n_stable} pixels; < 1000 minimum"
            )

        # 5. Per-epoch: download SAFE, orbit, OPERA ref (first epoch only for amplitude sanity)
        burst_out = CACHE / "output" / cfg.aoi_name
        burst_out.mkdir(parents=True, exist_ok=True)
        # compass writes nested <burst_id>/<YYYYMMDD>/<burst_id>_<YYYYMMDD>.h5,
        # so ensure_resume_safe's flat iterdir can't see them.
        have_all_epochs = (
            len(list(burst_out.rglob("*.h5"))) >= len(cfg.sensing_window)
        )
        if not have_all_epochs:
            for epoch_idx, epoch in enumerate(cfg.sensing_window):
                safe = find_cached_safe(
                    _safe_granule_for_epoch(cfg.burst_id, epoch),
                    cfg.cached_safe_search_dirs,
                )
                if safe is None:
                    safe = _download_safe_for_epoch(cfg.burst_id, epoch, CACHE / "input")
                elif not validate_safe_path(safe):
                    logger.warning("Ignoring invalid cached SAFE hit {}", safe)
                    safe = _download_safe_for_epoch(cfg.burst_id, epoch, CACHE / "input")
                # fetch_orbit takes (sensing_time, satellite, output_dir); pass epoch
                # explicitly rather than the SAFE path.
                orbit = fetch_orbit(
                    sensing_time=epoch,
                    satellite="S1A",
                    output_dir=CACHE / "orbits",
                )
                if epoch_idx == 0 and cfg.run_amplitude_sanity:
                    # D-07 amplitude sanity reference lookup is also repeated
                    # later on warm CSLC-cache paths, so this is just an eager
                    # fetch while first-epoch inputs are already being prepared.
                    _ensure_opera_reference_for_first_epoch(cfg)
                # run_cslc calls subsideo._mp.configure_multiprocessing() at
                # its top (Phase 1 D-14), so no explicit call needed here.
                run_cslc(
                    safe_paths=[safe],
                    orbit_path=orbit,
                    dem_path=dem_path,
                    burst_ids=[cfg.burst_id],
                    output_dir=burst_out,
                    burst_database_file=EU_BURST_DB_PATH,
                )

        # 6. IFG coherence stack
        # compass writes outputs nested as <burst_out>/<burst_id>/<YYYYMMDD>/
        # <burst_id>_<YYYYMMDD>.h5, so recurse.
        cslc_h5s = sorted(burst_out.rglob("*.h5"))
        ifgrams_stack = _compute_ifg_coherence_stack(cslc_h5s, boxcar_px=5)

        # Reproject stable_mask (DEM grid, ~30m) onto the CSLC output grid
        # (OPERA 5m range × 10m azimuth per compass runconfig). coherence_stats
        # + residual_mean_velocity boolean-index the coherence stack, which is
        # on the CSLC grid, so the mask must match.
        import h5py  # noqa: PLC0415
        from affine import Affine  # noqa: PLC0415
        from rasterio.warp import Resampling, reproject  # noqa: PLC0415

        with h5py.File(cslc_h5s[0], "r") as _f:
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

        # Intersect with CSLC valid-data mask. The rectangular CSLC grid has
        # NaN/zero corners outside the burst parallelogram footprint;
        # coherence is structurally 0 there. Derived from the coherence stack
        # itself to avoid re-reading the h5.
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

        coh_stats = coherence_stats(ifgrams_stack, stable_mask_cslc, coherence_threshold=0.6)

        # 7. Residual velocity (linear-fit per D-Claude's-Discretion)
        velocity_raster = compute_residual_velocity(
            cslc_h5s,
            stable_mask_cslc,
            sensing_dates=list(cfg.sensing_window),
        )
        residual = residual_mean_velocity(velocity_raster, stable_mask_cslc, frame_anchor="median")

        # 8. Amplitude sanity -- gated on per-AOI run_amplitude_sanity flag (D-07)
        ra_result: ReferenceAgreementResultJson | None = None
        amplitude_blocker: CSLCBlockerEvidence | None = None
        if cfg.run_amplitude_sanity:
            ref_dir = CACHE / "opera_reference" / cfg.aoi_name
            ref_h5_candidates = _ensure_opera_reference_for_first_epoch(cfg)
            if ref_h5_candidates:
                opera_ref_h5 = ref_h5_candidates[0]
                cmp_result = compare_cslc(
                    product_path=cslc_h5s[0],
                    reference_path=opera_ref_h5,
                )
                ra_result = ReferenceAgreementResultJson(
                    measurements={
                        "amplitude_r": cmp_result.reference_agreement.measurements.get(
                            "amplitude_r", float("nan")
                        ),
                        "amplitude_rmse_db": cmp_result.reference_agreement.measurements.get(
                            "amplitude_rmse_db", float("nan")
                        ),
                    },
                    criterion_ids=["cslc.amplitude_r_min", "cslc.amplitude_rmse_db_max"],
                )
            else:
                logger.warning(
                    "Amplitude sanity skipped for {} -- no OPERA reference HDF5 found "
                    "(OPERA CSLC-S1 V1 is N.Am. only; EU AOI amplitude sanity is best-effort)",
                    cfg.aoi_name,
                )
                amplitude_blocker = CSLCBlockerEvidence(
                    reason_code="opera_frame_unavailable",
                    evidence={
                        "aoi_name": cfg.aoi_name,
                        "burst_id": cfg.burst_id,
                        "reference_h5_count": 0,
                        "reference_dir": str(ref_dir),
                    },
                )

        # 9. Stable-mask sanity artifacts (P2.1 mitigation) — use the CSLC-grid
        # stable_mask so per-pixel-mean coherence indexing matches the stack.
        _write_sanity_artifacts(
            cfg.aoi_name,
            stable_mask=stable_mask_cslc,
            coherence_stack=ifgrams_stack,
            transform=cslc_transform,
            crs=cslc_crs,
            out_dir=CACHE / "sanity" / cfg.aoi_name,
            stable_mask_diagnostics=stable_mask_diagnostics,
        )

        # --- EU-ONLY: EGMS L2a stable-PS residual step (CSLC-05 third number; D-12) ---
        egms_csvs: list[Path] = []
        egms_residual: float | None = None
        egms_l2a_diagnostics: dict[str, object] = {}
        egms_l2a_blocker: CSLCBlockerEvidence | None = None
        egms_toolkit_version = "unknown"
        try:
            import EGMStoolkit  # noqa: PLC0415

            egms_toolkit_version = getattr(EGMStoolkit, "__version__", "unknown")
        except ImportError:
            egms_toolkit_version = "import_failed"
        try:
            egms_csvs = _fetch_egms_l2a(bounds, out_dir=CACHE / "egms" / cfg.aoi_name)
            if egms_csvs:
                # velocity_raster was computed above; persist as GeoTIFF so
                # compare_cslc_egms_l2a_residual can rasterio.open it.
                # velocity_raster is on the CSLC grid (from compute_residual_velocity);
                # use cslc_transform/cslc_crs to write it as a georeferenced GeoTIFF.
                velocity_tif = _write_velocity_geotiff(
                    velocity_raster,
                    cslc_transform,
                    cslc_crs,
                    out_path=CACHE / "output" / cfg.aoi_name / "velocity.tif",
                )
                egms_l2a_diagnostics = compare_cslc_egms_l2a_residual_diagnostics(
                    velocity_tif,
                    egms_csvs,
                    stable_std_max=2.0,
                    min_valid_points=100,
                )
                if egms_l2a_diagnostics["blocker_reason"] is None:
                    egms_residual = float(egms_l2a_diagnostics["residual_mm_yr"])
                    logger.info(
                        "EGMS L2a residual on {} stable PS: {:.3f} mm/yr",
                        cfg.aoi_name,
                        egms_residual,
                    )
                else:
                    egms_blocker_evidence = {
                        **{
                            k: v
                            for k, v in egms_l2a_diagnostics.items()
                            if k != "blocker_reason"
                        },
                        "request_bounds": repr(bounds),
                        "egms_toolkit_version": egms_toolkit_version,
                        "retry_attempts": 0,
                        "retry_evidence": "not_applicable_fetch_succeeded",
                        "error": None,
                    }
                    egms_l2a_blocker = CSLCBlockerEvidence(
                        reason_code="egms_l2a_"
                        + str(egms_l2a_diagnostics["blocker_reason"]),
                        evidence=egms_blocker_evidence,
                    )
            else:
                logger.warning(
                    "EGMS L2a: no CSVs downloaded for {} -- skipping third-number",
                    cfg.aoi_name,
                )
        except Exception as e:  # noqa: BLE001
            logger.error("EGMS L2a residual step FAILED for {}: {}", cfg.aoi_name, e)
            egms_residual = None
            egms_l2a_blocker = CSLCBlockerEvidence(
                reason_code="egms_l2a_upstream_access_or_tooling_failure",
                evidence={
                    "request_bounds": repr(bounds),
                    "egms_toolkit_version": egms_toolkit_version,
                    "retry_attempts": 1,
                    "retry_evidence": (
                        "single existing _fetch_egms_l2a invocation failed before "
                        "CSV diagnostics"
                    ),
                    "n_ps_total": None,
                    "n_stable_ps": None,
                    "n_in_raster": None,
                    "n_valid": None,
                    "stable_std_max": 2.0,
                    "min_valid_points": 100,
                    "error": repr(e),
                },
            )

        # --- Build AOIResult with THREE-number product_quality (CSLC-05) ---
        pq_measurements: dict[str, float] = {
            "coherence_median_of_persistent": coh_stats["median_of_persistent"],
            "residual_mm_yr": residual,
            # diagnostics (not gate-critical)
            "coherence_mean": coh_stats["mean"],
            "coherence_median": coh_stats["median"],
            "coherence_p25": coh_stats["p25"],
            "coherence_p75": coh_stats["p75"],
            "persistently_coherent_fraction": coh_stats["persistently_coherent_fraction"],
        }
        if egms_residual is not None and not math.isnan(egms_residual):
            pq_measurements["egms_l2a_stable_ps_residual_mm_yr"] = egms_residual

        pq = ProductQualityResultJson(
            measurements=pq_measurements,
            criterion_ids=[
                "cslc.selfconsistency.coherence_min",
                "cslc.selfconsistency.residual_mm_yr_max",
                # NOTE: no 'cslc.egms_l2a.residual_mm_yr_max' criterion entry --
                # CONTEXT D-12 / PATTERNS ship the EGMS residual as reported-only for
                # first-rollout (not in criteria.py); CSLC-05 gating uses the shared
                # cslc.selfconsistency.residual_mm_yr_max criterion.
            ],
        )
        return AOIResult(
            aoi_name=cfg.aoi_name,
            regime=cfg.regime,
            burst_id=cfg.burst_id,
            sensing_window=[e.isoformat() for e in cfg.sensing_window],
            status="CALIBRATING",   # D-03 first-rollout -- never PASS/FAIL in Phase 3
            stable_mask_pixels=n_stable,
            product_quality=pq,
            reference_agreement=ra_result,
            candidate_binding=_candidate_binding_for_pq(
                pq,
                egms_l2a_blocker=egms_l2a_blocker,
                amplitude_blocker=amplitude_blocker,
            ),
        )

    # -- Main loop --------------------------------------------------------

    per_aoi: list[AOIResult] = []
    per_aoi_input_hashes: dict[str, dict[str, str]] = {}
    for cfg in AOIS:
        t0 = time.time()
        try:
            row = process_aoi(cfg)
            per_aoi.append(row)
            per_aoi_input_hashes[cfg.aoi_name] = _collect_input_hashes(cfg)
            logger.info("AOI {} {} in {:.0f}s", cfg.aoi_name, row.status, time.time() - t0)
        except Exception as e:  # noqa: BLE001
            tb = traceback.format_exc()
            logger.error("AOI {} FAIL ({:.0f}s): {}", cfg.aoi_name, time.time() - t0, e)
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

    # Aggregate reduce
    pass_count = sum(1 for r in per_aoi if r.status in ("PASS", "CALIBRATING"))
    total = len(per_aoi)
    any_blocker = any(r.status == "BLOCKER" for r in per_aoi)
    cell_status = _resolve_cell_status(per_aoi)

    pq_agg = _worst_pq(per_aoi)
    ra_agg = _worst_ra(per_aoi)

    metrics = CSLCSelfConsistEUCellMetrics(
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
    (CACHE / "metrics.json").write_text(metrics.model_dump_json(indent=2))

    # meta.json provenance
    git_sha, git_dirty = get_git_sha()
    meta = MetaJson(
        git_sha=git_sha,
        git_dirty=git_dirty,
        run_started_iso=run_started_iso,
        run_duration_s=time.time() - run_started,
        python_version=sys.version,
        platform=platform.platform(),
        input_hashes={k: v for d in per_aoi_input_hashes.values() for k, v in d.items()},
    )
    (CACHE / "meta.json").write_text(meta.model_dump_json(indent=2))

    # Summary banner
    print(f"\n{'='*70}")
    print(
        f"eval-cslc-selfconsist-eu: {pass_count}/{total} {cell_status}",
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
        egms_res = (
            row.product_quality.measurements.get(
                "egms_l2a_stable_ps_residual_mm_yr", float("nan")
            )
            if row.product_quality
            else float("nan")
        )
        print(
            f"  [{row.status}] {row.aoi_name:15s} "
            f"coh={coh:.3f} residual={res:+.2f} mm/yr egms={egms_res:+.2f} mm/yr"
        )
    print("=" * 70)

    # Exit code: CALIBRATING + MIXED both count as success exit.
    # BLOCKER surfaces via matrix writer warning glyph; supervisor distinguishes 124 = watchdog.
    sys.exit(0 if cell_status in ("PASS", "CALIBRATING", "MIXED") else 1)
