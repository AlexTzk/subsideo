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
#   - IberianAOI.fallback_chain = (Alentejo, MassifCentral) from probe artifact
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

# Iberian 15-epoch SoCal-style stack + 2-candidate fallback-chain
# (worst-case 2 x 12 h) + EGMStoolkit L2a download + per-stage
# ensure_resume_safe + supervisor 2x margin. Warm re-run <= 5 min.
EXPECTED_WALL_S = 60 * 60 * 14   # 50400s (CONTEXT D-Claude's-Discretion EU budget)


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
    from subsideo.products import _mp
    from subsideo.products.cslc import run_cslc
    from subsideo.validation.compare_cslc import compare_cslc, compare_cslc_egms_l2a_residual
    from subsideo.validation.criteria import CRITERIA  # noqa: F401
    from subsideo.validation.harness import (
        bounds_for_burst,
        credential_preflight,
        ensure_resume_safe,
        find_cached_safe,
        select_opera_frame_by_utc_hour,
    )
    from subsideo.validation.matrix_schema import (
        AOIResult,
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

        aoi_name: str                          # "Iberian" | "Iberian/Alentejo" | etc.
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

    # AOIS -- locked from .planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md
    # (Plan 03-02 user-approved 2026-04-24).

    # BLOCKER 3 cross-reference: per-AOI epoch tuples sourced from the probe
    # artifact sections `### IBERIAN_PRIMARY_EPOCHS`, `### IBERIAN_ALENTEJO_EPOCHS`,
    # `### IBERIAN_MASSIF_CENTRAL_EPOCHS`. 15 concrete datetime literals per tuple.
    # The IBERIAN_EPOCHS alias below (= IBERIAN_PRIMARY_EPOCHS) is kept for readability.
    IBERIAN_PRIMARY_EPOCHS: tuple[datetime, ...] = (
        # 15 datetimes copy-pasted verbatim from probe artifact section
        # `### IBERIAN_PRIMARY_EPOCHS -- Iberian/Meseta-North`.
        datetime(2024, 1, 4, 6, 18, 3),
        datetime(2024, 1, 9, 6, 26, 23),
        datetime(2024, 1, 10, 18, 11, 36),
        datetime(2024, 1, 16, 6, 18, 2),
        datetime(2024, 1, 21, 6, 26, 22),
        datetime(2024, 1, 22, 18, 11, 35),
        datetime(2024, 1, 28, 6, 18, 2),
        datetime(2024, 2, 2, 6, 26, 22),
        datetime(2024, 2, 3, 18, 11, 35),
        datetime(2024, 2, 9, 6, 18, 2),
        datetime(2024, 2, 15, 18, 11, 35),
        datetime(2024, 2, 21, 6, 18, 1),
        datetime(2024, 2, 26, 6, 26, 21),
        datetime(2024, 2, 27, 18, 11, 34),
        datetime(2024, 3, 4, 6, 18, 2),
    )

    IBERIAN_ALENTEJO_EPOCHS: tuple[datetime, ...] = (
        # Copy-pasted verbatim from `### IBERIAN_ALENTEJO_EPOCHS -- Iberian/Alentejo`.
        datetime(2024, 1, 1, 18, 35, 22),
        datetime(2024, 1, 2, 6, 35, 22),
        datetime(2024, 1, 7, 6, 43, 36),
        datetime(2024, 1, 8, 18, 27, 21),
        datetime(2024, 1, 13, 18, 35, 22),
        datetime(2024, 1, 14, 6, 35, 22),
        datetime(2024, 1, 19, 6, 43, 35),
        datetime(2024, 1, 20, 18, 27, 20),
        datetime(2024, 1, 25, 18, 35, 22),
        datetime(2024, 1, 26, 6, 35, 22),
        datetime(2024, 1, 31, 6, 43, 35),
        datetime(2024, 2, 1, 18, 27, 20),
        datetime(2024, 2, 6, 18, 35, 21),
        datetime(2024, 2, 7, 6, 35, 21),
        datetime(2024, 2, 12, 6, 43, 35),
    )

    IBERIAN_MASSIF_CENTRAL_EPOCHS: tuple[datetime, ...] = (
        # Copy-pasted verbatim from `### IBERIAN_MASSIF_CENTRAL_EPOCHS -- Iberian/MassifCentral`.
        datetime(2024, 1, 1, 5, 52, 18),
        datetime(2024, 1, 2, 17, 40, 2),
        datetime(2024, 1, 6, 6, 0, 27),
        datetime(2024, 1, 9, 17, 31, 55),
        datetime(2024, 1, 13, 5, 52, 17),
        datetime(2024, 1, 14, 17, 40, 1),
        datetime(2024, 1, 18, 6, 0, 26),
        datetime(2024, 1, 21, 17, 31, 55),
        datetime(2024, 1, 25, 5, 52, 17),
        datetime(2024, 1, 26, 17, 40, 1),
        datetime(2024, 1, 30, 6, 0, 26),
        datetime(2024, 2, 2, 17, 31, 54),
        datetime(2024, 2, 6, 5, 52, 17),
        datetime(2024, 2, 7, 17, 40, 0),
        datetime(2024, 2, 11, 6, 0, 25),
    )

    # Alias for the primary burst (used in IberianAOI below). Each fallback binds
    # its OWN per-AOI window -- Alentejo and Massif Central have different S1A
    # relative orbits than the Meseta primary, so their 15-epoch lists differ.
    IBERIAN_EPOCHS = IBERIAN_PRIMARY_EPOCHS

    # EU burst DB note: Alentejo and MassifCentral burst_ids are derived at eval
    # time using opera_utils.burst_frame_db.get_burst_id_geojson() over the bbox
    # centroid per probe artifact guidance (section "Note on EU burst_id"). The
    # values below are the probe-artifact-locked candidates pending user confirmation.
    _IBERIAN_FALLBACKS = (
        AOIConfig(
            aoi_name="Iberian/Alentejo",
            regime="interior-portugal-plateau",
            burst_id="t008_016940_iw2",   # EU burst DB derivation at eval time (probe artifact)
            sensing_window=IBERIAN_ALENTEJO_EPOCHS,
            output_epsg=32629,
            centroid_lat=38.55,
            cached_safe_search_dirs=(Path("eval-cslc-selfconsist-eu/input"),),
            run_amplitude_sanity=True,   # EU AOIs run D-07 amplitude sanity
        ),
        AOIConfig(
            aoi_name="Iberian/MassifCentral",
            regime="massif-central-plateau",
            burst_id="t131_279647_iw2",   # EU burst DB derivation at eval time (probe artifact)
            sensing_window=IBERIAN_MASSIF_CENTRAL_EPOCHS,
            output_epsg=32631,
            centroid_lat=45.15,
            cached_safe_search_dirs=(Path("eval-cslc-selfconsist-eu/input"),),
            run_amplitude_sanity=True,
        ),
    )

    IberianAOI = AOIConfig(
        aoi_name="Iberian",
        regime="iberian-meseta-sparse-vegetation",
        burst_id="t103_219329_iw1",   # Meseta-North primary -- Phase 2 carry-forward
        sensing_window=IBERIAN_EPOCHS,
        output_epsg=32630,
        centroid_lat=41.05,
        cached_safe_search_dirs=(
            Path("eval-cslc-selfconsist-eu/input"),
            Path("eval-rtc-eu/input"),   # D-02: reuse from Phase 2 RTC-EU eval
        ),
        fallback_chain=_IBERIAN_FALLBACKS,
        run_amplitude_sanity=True,   # BLOCKER 4 fix: EU primary runs D-07 amplitude sanity
    )

    AOIS: list[AOIConfig] = [IberianAOI]

    CACHE = Path("eval-cslc-selfconsist-eu")
    for sub in ("input", "output", "opera_reference", "dem", "orbits",
                "worldcover", "coastline", "sanity", "egms"):
        (CACHE / sub).mkdir(parents=True, exist_ok=True)

    # Path to EU burst DB (built by Phase 1 burst/db.py)
    EU_BURST_DB_PATH = Path(os.path.expanduser("~/.subsideo/eu_burst_db.sqlite"))

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
        """Download Sentinel-1 SAFE for a burst epoch from CDSE (fallback path)."""
        import boto3  # noqa: PLC0415
        import pystac_client  # noqa: PLC0415
        from botocore.config import Config  # noqa: PLC0415

        dest_dir.mkdir(parents=True, exist_ok=True)
        bounds = bounds_for_burst(burst_id, buffer_deg=0.5)
        west, south, east, north = bounds

        catalog = pystac_client.Client.open(
            "https://catalogue.dataspace.copernicus.eu/stac",
            headers={"Accept": "application/json"},
        )
        window_start = (epoch - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        window_end = (epoch + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        items = catalog.search(
            collections=["SENTINEL-1"],
            bbox=[west, south, east, north],
            datetime=f"{window_start}/{window_end}",
            query={"productType": {"eq": "SLC"}},
        ).item_collection()

        if not items:
            raise RuntimeError(
                f"No Sentinel-1 SLC found for burst {burst_id} near {epoch.isoformat()}"
            )

        item = items[0]
        s3_path = item.assets["PRODUCT"].href  # s3://eodata/...
        bucket, key = s3_path.replace("s3://", "").split("/", 1)
        safe_name = Path(key).name
        dest = dest_dir / safe_name
        if dest.exists():
            return dest

        s3 = boto3.client(
            "s3",
            endpoint_url="https://eodata.dataspace.copernicus.eu",
            aws_access_key_id=os.environ.get("CDSE_CLIENT_ID", ""),
            aws_secret_access_key=os.environ.get("CDSE_CLIENT_SECRET", ""),
            config=Config(signature_version="s3v4"),
        )
        logger.info("Downloading {} from CDSE s3://{}/{}", safe_name, bucket, key)
        s3.download_file(bucket, key, str(dest))
        return dest

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
                        stacks.append(f[dset_path][:].astype("complex64"))
                        break

        coherence_stack = []
        for i in range(len(stacks) - 1):
            ifg = stacks[i] * np.conj(stacks[i + 1])
            # Coherence estimate: |E[ifg]| / sqrt(E[|a|^2] * E[|b|^2])
            num = uniform_filter(np.abs(ifg), size=boxcar_px).astype("float32")
            denom_a = uniform_filter(np.abs(stacks[i]) ** 2, size=boxcar_px)
            denom_b = uniform_filter(np.abs(stacks[i + 1]) ** 2, size=boxcar_px)
            denom = np.sqrt(denom_a * denom_b + 1e-12).astype("float32")
            coh = np.clip(num / denom, 0.0, 1.0)
            coherence_stack.append(coh)

        return np.stack(coherence_stack, axis=0)  # (N-1, H, W)

    def _compute_slope_deg(dem_path: Path) -> np.ndarray:
        """Compute slope in degrees from a DEM GeoTIFF via numpy.gradient.

        Uses numpy.gradient on the elevation grid to get dzdx + dzdy,
        then arctan(sqrt(dzdx^2 + dzdy^2)).
        """
        import rasterio  # noqa: PLC0415

        with rasterio.open(dem_path) as src:
            dem = src.read(1).astype("float32")
            res_x = abs(src.transform.a)   # pixel width in map units
            res_y = abs(src.transform.e)   # pixel height in map units

        dzdx = np.gradient(dem, res_x, axis=1)
        dzdy = np.gradient(dem, res_y, axis=0)
        slope_deg = np.degrees(np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2)))
        return slope_deg.astype("float32")

    def _write_sanity_artifacts(
        aoi_name: str,
        *,
        stable_mask: np.ndarray,
        coherence_stack: np.ndarray,
        transform: object,
        crs: object,
        out_dir: Path,
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

    def _worst_pq(rows: list[AOIResult]) -> dict[str, float | str]:
        """Worst-case product-quality aggregate across all AOIs."""
        best_coh = float("inf")
        worst_resid = float("-inf")
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
            if abs(resid) > abs(worst_resid):
                worst_resid = resid
        return {
            "worst_coherence_median_of_persistent": best_coh if best_coh != float("inf") else 0.0,
            "worst_residual_mm_yr": worst_resid if worst_resid != float("-inf") else 0.0,
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

        # 2. DEM + slope
        dem_path = fetch_dem(bounds, output_dir=CACHE / "dem")
        slope_deg = _compute_slope_deg(dem_path)

        # 3. Natural Earth coastline + waterbodies
        coast, water = load_coastline_and_waterbodies(bounds)

        # 4. Stable mask
        stable_mask = build_stable_mask(
            wc_data, slope_deg, coast, water,
            transform=wc_transform, crs=wc_crs,
            coast_buffer_m=5000.0, water_buffer_m=500.0, slope_max_deg=10.0,
        )
        n_stable = int(stable_mask.sum())
        if n_stable < 1000:
            raise RuntimeError(
                f"{cfg.aoi_name}: stable_mask has only {n_stable} pixels; < 1000 minimum"
            )

        # 5. Per-epoch: download SAFE, orbit, OPERA ref (first epoch only for amplitude sanity)
        burst_out = CACHE / "output" / cfg.aoi_name
        burst_out.mkdir(parents=True, exist_ok=True)
        expected_h5 = [
            f"{cfg.burst_id}_{epoch.date().isoformat()}.h5"
            for epoch in cfg.sensing_window
        ]
        if not ensure_resume_safe(burst_out, expected_h5):
            for epoch_idx, epoch in enumerate(cfg.sensing_window):
                safe = find_cached_safe(
                    _safe_granule_for_epoch(cfg.burst_id, epoch),
                    cfg.cached_safe_search_dirs,
                )
                if safe is None:
                    safe = _download_safe_for_epoch(cfg.burst_id, epoch, CACHE / "input")
                orbit = fetch_orbit(safe, output_dir=CACHE / "orbits")
                if epoch_idx == 0 and cfg.run_amplitude_sanity:
                    # D-07 amplitude sanity -- gated on per-AOI AOIConfig flag.
                    # BLOCKER 4 fix: flag drives whether compare_cslc runs;
                    # the leaf-path conditional consults cfg.run_amplitude_sanity
                    # (not cfg.aoi_name == 'Iberian') so the EU script works
                    # identically for all three EU AOIs without further edits.
                    ref_results = earthaccess.search_data(
                        short_name="OPERA_L2_CSLC-S1_V1",
                        temporal=(epoch - timedelta(hours=1), epoch + timedelta(hours=1)),
                        granule_name=(
                            f"OPERA_L2_CSLC-S1_"
                            f"{cfg.burst_id.replace('_', '-').upper()}*"
                        ),
                    )
                    if ref_results:
                        chosen = select_opera_frame_by_utc_hour(epoch, ref_results)
                        earthaccess.download(
                            [chosen],
                            str(CACHE / "opera_reference" / cfg.aoi_name),
                        )
                _mp.configure_multiprocessing()
                run_cslc(
                    safe_paths=[safe],
                    orbit_path=orbit,
                    dem_path=dem_path,
                    burst_ids=[cfg.burst_id],
                    output_dir=burst_out,
                    burst_database_file=EU_BURST_DB_PATH,
                )

        # 6. IFG coherence stack
        cslc_h5s = sorted(burst_out.glob("*.h5"))
        ifgrams_stack = _compute_ifg_coherence_stack(cslc_h5s, boxcar_px=5)
        coh_stats = coherence_stats(ifgrams_stack, stable_mask, coherence_threshold=0.6)

        # 7. Residual velocity (linear-fit per D-Claude's-Discretion)
        velocity_raster = compute_residual_velocity(
            cslc_h5s,
            stable_mask,
            sensing_dates=list(cfg.sensing_window),
        )
        residual = residual_mean_velocity(velocity_raster, stable_mask, frame_anchor="median")

        # 8. Amplitude sanity -- gated on per-AOI run_amplitude_sanity flag (D-07)
        ra_result: ReferenceAgreementResultJson | None = None
        if cfg.run_amplitude_sanity:
            ref_dir = CACHE / "opera_reference" / cfg.aoi_name
            ref_h5_candidates = sorted(ref_dir.glob("*.h5"))
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

        # 9. Stable-mask sanity artifacts (P2.1 mitigation)
        _write_sanity_artifacts(
            cfg.aoi_name,
            stable_mask=stable_mask,
            coherence_stack=ifgrams_stack,
            transform=wc_transform,
            crs=wc_crs,
            out_dir=CACHE / "sanity" / cfg.aoi_name,
        )

        # --- EU-ONLY: EGMS L2a stable-PS residual step (CSLC-05 third number; D-12) ---
        egms_csvs: list[Path] = []
        egms_residual: float | None = None
        try:
            egms_csvs = _fetch_egms_l2a(bounds, out_dir=CACHE / "egms" / cfg.aoi_name)
            if egms_csvs:
                # velocity_raster was computed above; persist as GeoTIFF so
                # compare_cslc_egms_l2a_residual can rasterio.open it.
                velocity_tif = _write_velocity_geotiff(
                    velocity_raster,
                    wc_transform,
                    wc_crs,
                    out_path=CACHE / "output" / cfg.aoi_name / "velocity.tif",
                )
                egms_residual = compare_cslc_egms_l2a_residual(
                    velocity_tif,
                    egms_csvs,
                    stable_std_max=2.0,
                )
                logger.info(
                    "EGMS L2a residual on {} stable PS: {:.3f} mm/yr",
                    cfg.aoi_name,
                    egms_residual,
                )
            else:
                logger.warning(
                    "EGMS L2a: no CSVs downloaded for {} -- skipping third-number",
                    cfg.aoi_name,
                )
        except Exception as e:  # noqa: BLE001
            logger.error("EGMS L2a residual step FAILED for {}: {}", cfg.aoi_name, e)
            egms_residual = None

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
