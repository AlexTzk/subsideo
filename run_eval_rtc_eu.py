# run_eval_rtc_eu.py -- EU RTC-S1 validation against OPERA L2 RTC-S1 reference
#
# Phase 2 (v1.1) deliverable. Proves Phase 1 harness on a deterministic
# product (RTC) across 5 EU terrain regimes (Alpine, Scandinavian, Iberian,
# TemperateFlat, Fire). Per-burst PASS/FAIL aggregated into a single matrix
# cell (`rtc:eu` in results/matrix_manifest.yml) and a single CONCLUSIONS
# doc (CONCLUSIONS_RTC_EU.md).
#
# Orchestration:
#   - Declarative BURSTS: list[BurstConfig] (D-05)
#   - Per-burst try/except isolation (D-06)
#   - Sequential across bursts (D-07: no burst-level parallelism)
#   - Per-burst whole-pipeline skip + per-stage ensure_resume_safe (D-08)
#   - Cached-SAFE reuse via harness.find_cached_safe (D-02)
#   - Single eval-rtc-eu/metrics.json (RTCEUCellMetrics; D-09, D-10)
#   - Single eval-rtc-eu/meta.json (per-burst input hashes flattened; D-12)
#
# RTC-01 mandatory constraints (P1.1 cached-bias prevention):
#   - >=1 burst with >1000 m relief: Alpine (expected ~3200 m relief)
#   - >=1 burst >55N:                Scandinavian (~67N)
# Both satisfied by the declarative BURSTS list below.
#
# RTC-02: reference-agreement criteria are FROZEN at v1.0 values
# (rtc.rmse_db_max < 0.5 dB; rtc.correlation_min > 0.99). This script
# does NOT introduce tightened gates. D-13 INVESTIGATION_TRIGGER entries
# are non-gates; they only set investigation_required + reason.
#
# Makefile target: `make eval-rtc-eu` -> supervisor wraps this script.
#   EXPECTED_WALL_S: 4h = 14400s covers 5 bursts with cold downloads and
#   variable network margin. Warm re-run: ~2 min (per-burst skip per D-08).
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

# 5 bursts x ~30 min cold + reference/DEM/orbit fetches + supervisor 2x margin.
# Actual wallclock from first cold run populates Plan 02-05 Task 1 checkpoint notes.
EXPECTED_WALL_S = 60 * 60 * 4   # 14400s; supervisor AST-parses (D-11 + T-07-06)


if __name__ == "__main__":
    import hashlib
    import json  # noqa: F401  -- reserved for future provenance extensions
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
    import rasterio
    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.rtc import run_rtc
    from subsideo.validation.compare_rtc import compare_rtc
    from subsideo.validation.criteria import CRITERIA
    from subsideo.validation.harness import (
        bounds_for_burst,
        credential_preflight,
        ensure_resume_safe,
        find_cached_safe,
        select_opera_frame_by_utc_hour,
        validate_safe_path,
    )
    from subsideo.validation.matrix_schema import (
        BurstResult,
        MetaJson,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
        RTCEUCellMetrics,
    )

    load_dotenv()

    credential_preflight([
        "EARTHDATA_USERNAME",
        "EARTHDATA_PASSWORD",
    ])
    # CDSE creds are only required for fresh EU SAFE downloads; not all
    # 5 bursts need CDSE when cached reuses hit (D-02). We accept a
    # runtime error per-burst rather than fail the whole cell upfront.

    # -- Configuration ----------------------------------------------------

    @dataclass(frozen=True)
    class BurstConfig:
        """Per-burst declarative config for run_eval_rtc_eu.BURSTS (D-05)."""
        burst_id: str                                                        # JPL lowercase
        regime: Literal["Alpine", "Scandinavian", "Iberian", "TemperateFlat", "Fire"]
        sensing_time: datetime                                               # UTC
        output_epsg: int                                                     # UTM zone
        centroid_lat: float
        relative_orbit: int | None                                           # ASF query hint
        cached_safe_search_dirs: tuple[Path, ...]                            # D-02

    # BURSTS -- locked from .planning/milestones/v1.1-research/rtc_eu_burst_candidates.md
    # (Plan 02-02, user-approved-as-drafted 2026-04-23). Each row mirrors the
    # approved probe artifact regime + centroid_lat + expected relief values.
    #
    # RTC-01 mandatory constraints (verified in tests/unit/test_rtc_eu_eval.py):
    #   >=1 burst with >1000 m relief -> row 0 (Alpine, expected ~3200 m relief).
    #   >=1 burst >55N                -> row 1 (Scandinavian, ~67N, >55 by 12 deg headroom).
    BURSTS: list[BurstConfig] = [
        # 1. Alpine (Swiss/Italian Alps, Valtellina) -- >1000 m relief, RTC-01 constraint.
        #    Expected max_relief ~3200 m computed at eval time from cached DEM.
        #    burst_id locked from live OPERA L2 RTC catalog query (2026-04-23); dominant
        #    burst over Valtellina AOI. Relorb 66 confirmed from granule track code.
        BurstConfig(
            burst_id="t066_140413_iw1",
            regime="Alpine",
            sensing_time=datetime(2024, 5, 2, 5, 35, 47),
            output_epsg=32632,            # UTM 32N
            centroid_lat=46.35,
            relative_orbit=66,
            cached_safe_search_dirs=(
                Path("eval-rtc-eu/input"),
            ),
        ),
        # 2. Scandinavian (Northern Sweden, Norrbotten, >55N) -- RTC-01 constraint.
        #    burst_id locked from live OPERA L2 RTC catalog query (2026-04-23); dominant
        #    burst over Norrbotten AOI. Track 058 descending (not 029 as originally
        #    drafted) -- OPERA coverage is heavier on this track over the AOI.
        BurstConfig(
            burst_id="t058_122828_iw3",
            regime="Scandinavian",
            sensing_time=datetime(2024, 5, 1, 16, 7, 25),
            output_epsg=32634,            # UTM 34N
            centroid_lat=67.15,
            relative_orbit=58,
            cached_safe_search_dirs=(
                Path("eval-rtc-eu/input"),
            ),
        ),
        # 3. Iberian arid (Meseta north of Madrid).
        #    burst_id locked from live OPERA L2 RTC catalog query (2026-04-23); dominant
        #    burst over Meseta AOI. Track 103 ascending (not 154 as originally drafted)
        #    -- OPERA coverage is heavier on this track over the AOI.
        BurstConfig(
            burst_id="t103_219329_iw1",
            regime="Iberian",
            sensing_time=datetime(2024, 5, 4, 18, 3, 39),
            output_epsg=32630,            # UTM 30N
            centroid_lat=41.15,
            relative_orbit=103,
            cached_safe_search_dirs=(
                Path("eval-rtc-eu/input"),
            ),
        ),
        # 4. Temperate flat (Bologna, Po plain) -- SAFE cached from DISP-EGMS (D-02).
        #    burst_id preserved from probe-draft (Bologna pattern from Phase 1
        #    DISP-EGMS). sensing_time lifted to 2024-05-05T17:07:05Z (first OPERA
        #    RTC granule for this burst in the archive). 2021-03-14 predates OPERA
        #    operational archive, so no reference is available for that epoch.
        BurstConfig(
            burst_id="t117_249422_iw2",
            regime="TemperateFlat",
            sensing_time=datetime(2024, 5, 5, 17, 7, 5),
            output_epsg=32632,            # UTM 32N
            centroid_lat=44.50,
            relative_orbit=117,
            cached_safe_search_dirs=(
                Path("eval-rtc-eu/input"),
                Path("eval-disp-egms/input"),    # D-02 cross-cell reuse
            ),
        ),
        # 5. Fire (Aveiro/Viseu 2024 footprint) -- SAFE cached from DIST-EU (D-02).
        #    burst_id locked from live OPERA L2 RTC catalog query (2026-04-23); dominant
        #    burst over Aveiro/Viseu AOI. Track 045 descending (not 154 as originally
        #    drafted) -- OPERA coverage is heavier on this track over the AOI.
        BurstConfig(
            burst_id="t045_094744_iw3",
            regime="Fire",
            sensing_time=datetime(2024, 5, 12, 18, 36, 21),
            output_epsg=32629,            # UTM 29N
            centroid_lat=40.70,
            relative_orbit=45,
            cached_safe_search_dirs=(
                Path("eval-rtc-eu/input"),
                Path("eval-dist-eu/input"),
                Path("eval-dist-eu-nov15/input"),
            ),
        ),
    ]

    CACHE = Path("eval-rtc-eu")
    CACHE.mkdir(exist_ok=True)
    (CACHE / "input").mkdir(exist_ok=True)
    (CACHE / "output").mkdir(exist_ok=True)
    (CACHE / "opera_reference").mkdir(exist_ok=True)
    (CACHE / "dem").mkdir(exist_ok=True)
    (CACHE / "orbits").mkdir(exist_ok=True)

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

    def compute_max_relief(dem_path: Path) -> float | None:
        """Max relief (m) = max - min elevation in the DEM."""
        try:
            with rasterio.open(dem_path) as src:
                data = src.read(1, masked=True)
                if data.count() == 0:
                    return None
                return float(data.max()) - float(data.min())
        except Exception as e:  # noqa: BLE001 - cache inspection, never fatal
            logger.warning("compute_max_relief({}): {}", dem_path, e)
            return None

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


    # -- Per-burst pipeline ---------------------------------------------

    def process_burst(cfg: BurstConfig) -> BurstResult:
        """Run the 5-stage RTC pipeline for one burst; return a BurstResult.

        Stages:
          1. OPERA reference discovery + download.
          2. S1 SAFE: find_cached_safe then fall back to ASF download.
          3. DEM fetch via dem-stitcher.
          4. POEORB orbit fetch.
          5. run_rtc -> compare_rtc -> BurstResult construction.
        """
        print("=" * 70)
        print(f"BURST {cfg.burst_id} ({cfg.regime}, {cfg.centroid_lat:.2f} degN)")
        print("=" * 70)

        burst_out = CACHE / "output" / cfg.burst_id
        burst_out.mkdir(parents=True, exist_ok=True)
        burst_opera_ref = CACHE / "opera_reference" / cfg.burst_id
        burst_opera_ref.mkdir(parents=True, exist_ok=True)

        bounds = bounds_for_burst(cfg.burst_id, buffer_deg=0.5)
        logger.info("Bounds for {}: {}", cfg.burst_id, bounds)

        # Stage 1: OPERA reference lookup (always via CMR; even on cache hit we
        # need the granule metadata to extract the canonical source SAFE in Stage 2)
        logger.info("Querying OPERA catalog for {}", cfg.burst_id)
        # Narrow window: +/- 1 day around sensing_time.
        temporal_start = cfg.sensing_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        # Convert JPL-lowercase burst_id to OPERA uppercase format for
        # granule filter: t144_308029_iw1 -> T144-308029-IW1.
        parts = cfg.burst_id.split("_")
        opera_burst_upper = f"T{parts[0][1:]}-{parts[1]}-{parts[2].upper()}"
        ref_results = earthaccess.search_data(
            short_name="OPERA_L2_RTC-S1_V1",
            temporal=(
                (cfg.sensing_time - timedelta(days=1)).strftime("%Y-%m-%d"),
                (cfg.sensing_time + timedelta(days=1)).strftime("%Y-%m-%d"),
            ),
            granule_name=f"OPERA_L2_RTC-S1_{opera_burst_upper}*",
        )
        if not ref_results:
            raise RuntimeError(
                f"No OPERA RTC granule found for {cfg.burst_id} "
                f"near {temporal_start}"
            )
        # earthaccess DataGranule objects are dict-like but nest the sensing
        # time under ``umm.TemporalExtent.RangeDateTime.BeginningDateTime``.
        # select_opera_frame_by_utc_hour expects a flat ``sensing_datetime``
        # key, so enrich each entry in-place before passing it through.
        for _g in ref_results:
            if "sensing_datetime" in _g:
                continue
            _umm = _g.get("umm", {}) if isinstance(_g, dict) else {}
            _rdt = _umm.get("TemporalExtent", {}).get("RangeDateTime", {})
            _beg = _rdt.get("BeginningDateTime")
            if _beg:
                _g["sensing_datetime"] = _beg
            # Give the frame an id that select_opera_frame_by_utc_hour
            # echoes back in "Multiple ..." errors for debuggability.
            if "id" not in _g and isinstance(_umm.get("GranuleUR"), str):
                _g["id"] = _umm["GranuleUR"]
        # select_opera_frame_by_utc_hour picks +/-1h; ensures unambiguous match.
        chosen = select_opera_frame_by_utc_hour(
            cfg.sensing_time, ref_results, tolerance_hours=1.0
        )

        # Download OPERA reference .tif if not already cached.
        opera_tifs = sorted(burst_opera_ref.glob("*.tif"))
        if not opera_tifs:
            logger.info("Downloading OPERA reference for {}", cfg.burst_id)
            earthaccess.download([chosen], str(burst_opera_ref))
            opera_tifs = sorted(burst_opera_ref.glob("*.tif"))
            if not opera_tifs:
                raise RuntimeError(
                    f"OPERA download produced no .tif for {cfg.burst_id}"
                )
        else:
            logger.info(
                "OPERA ref cached for {}: {}",
                cfg.burst_id, [p.name for p in opera_tifs],
            )
        opera_vv = next((p for p in opera_tifs if "VV" in p.name), opera_tifs[0])

        # Stage 2: S1 SAFE -- canonical source from OPERA CMR metadata
        # (find_cached_safe first; fall back to ASF download).
        #
        # OPERA RTC granule CMR records expose a ``umm.InputGranules`` list
        # naming the exact Sentinel-1 SLC slice used as input. That slice is
        # the only SAFE guaranteed to contain the burst for opera-rtc's
        # ``runconfig_to_bursts`` step (S1 IW slices are ~28 s long and
        # overlap by ~2 s, so burst-to-slice membership is NOT reliably
        # inferred from start/stop-time heuristics -- see commit history for
        # run_eval_rtc_eu.py debug notes).
        chosen_umm = chosen.get("umm", {}) if isinstance(chosen, dict) else {}
        input_granules = chosen_umm.get("InputGranules") or []
        source_granule = None
        for _ig in input_granules:
            ig_str = str(_ig)
            if ig_str.startswith("S1") and "_SLC_" in ig_str:
                source_granule = ig_str
                break
        if not source_granule:
            # Defensive fallback: if OPERA metadata does not carry an S1 SLC
            # reference (unexpected for operational products), fall back to
            # a containment-based ASF search.
            logger.warning(
                "OPERA granule for {} has no S1 SLC in InputGranules ({!r}); "
                "falling back to ASF containment search",
                cfg.burst_id, input_granules,
            )
            slc_search_start = (cfg.sensing_time - timedelta(minutes=5)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            slc_search_end = (cfg.sensing_time + timedelta(minutes=5)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            kwargs: dict[str, object] = dict(
                platform=asf.PLATFORM.SENTINEL1,
                processingLevel="SLC",
                beamMode="IW",
                start=slc_search_start,
                end=slc_search_end,
                maxResults=10,
            )
            if cfg.relative_orbit is not None:
                kwargs["relativeOrbit"] = cfg.relative_orbit
            slc_results = asf.search(**kwargs)  # type: ignore[arg-type]
            if not slc_results:
                raise RuntimeError(
                    f"No S1 SLC found on ASF for {cfg.burst_id} "
                    f"around {cfg.sensing_time}"
                )
            containing = [
                r for r in slc_results
                if datetime.fromisoformat(
                    str(r.properties["startTime"]).rstrip("Z")
                ) <= cfg.sensing_time <= datetime.fromisoformat(
                    str(r.properties["stopTime"]).rstrip("Z")
                )
            ]
            if not containing:
                raise RuntimeError(
                    f"No SAFE contains sensing_time={cfg.sensing_time} "
                    f"for {cfg.burst_id} (fallback path; InputGranules was "
                    f"{input_granules!r})"
                )
            # If multiple SAFEs contain sensing_time (slice-edge overlap),
            # prefer the one whose midpoint is closest to sensing_time.
            scene = min(
                containing,
                key=lambda r: abs(
                    (
                        datetime.fromisoformat(str(r.properties["startTime"]).rstrip("Z"))
                        + (
                            datetime.fromisoformat(str(r.properties["stopTime"]).rstrip("Z"))
                            - datetime.fromisoformat(str(r.properties["startTime"]).rstrip("Z"))
                        ) / 2
                    ) - cfg.sensing_time
                ),
            )
            granule_id = str(scene.properties["fileID"]).removesuffix("-SLC")
        else:
            granule_id = source_granule
            # Resolve the ASF product for the exact SAFE named in InputGranules.
            slc_results = asf.search(
                granule_list=[source_granule], processingLevel="SLC"
            )
            if not slc_results:
                raise RuntimeError(
                    f"ASF cannot resolve OPERA source SAFE {source_granule!r} "
                    f"for {cfg.burst_id}"
                )
            scene = slc_results[0]
        _src_tag = "InputGranules" if source_granule else "fallback"
        logger.info(
            "ASF chose {} (start={}, source={})",
            granule_id, scene.properties["startTime"], _src_tag,
        )

        cached_safe = find_cached_safe(
            granule_id, list(cfg.cached_safe_search_dirs)
        )
        if cached_safe is not None:
            safe_path = cached_safe
            cached = True
            logger.info("SAFE cache hit for {}: {}", cfg.burst_id, safe_path)
        else:
            cached = False
            local_input = CACHE / "input"
            safe_path = local_input / f"{granule_id}.zip"
            if not safe_path.exists():
                logger.info(
                    "Downloading SAFE from ASF (~4 GB): {}", granule_id
                )
                session = asf.ASFSession().auth_with_creds(
                    username=os.environ["EARTHDATA_USERNAME"],
                    password=os.environ["EARTHDATA_PASSWORD"],
                )
                scene.download(path=str(local_input), session=session)
                zips = sorted(local_input.glob(f"{granule_id}*.zip"))
                if not zips:
                    raise RuntimeError(
                        f"ASF download failed for {granule_id}: "
                        f"no zip in {local_input}"
                    )
                safe_path = zips[-1]
            if not validate_safe_path(safe_path, remove_invalid=True):
                raise RuntimeError(
                    f"SAFE failed integrity validation before RTC processing: {safe_path}"
                )
            logger.info(
                "SAFE ready for {}: {} ({:.2f} GB)",
                cfg.burst_id, safe_path, safe_path.stat().st_size / 1e9,
            )

        # Stage 3: DEM
        dem_burst_dir = CACHE / "dem" / cfg.burst_id
        dem_burst_dir.mkdir(parents=True, exist_ok=True)
        dem_tifs = sorted(dem_burst_dir.glob("*.tif"))
        if dem_tifs:
            dem_path = dem_tifs[0]
            logger.info("DEM cached for {}: {}", cfg.burst_id, dem_path.name)
        else:
            dem_path, _ = fetch_dem(
                bounds=list(bounds),
                output_epsg=cfg.output_epsg,
                output_dir=dem_burst_dir,
            )
            logger.info("DEM fetched for {}: {}", cfg.burst_id, dem_path.name)

        # Stage 4: Orbit
        sat_letter = granule_id[:3]  # "S1A" or "S1B"
        orbit_path = fetch_orbit(
            sensing_time=cfg.sensing_time,
            satellite=sat_letter,
            output_dir=CACHE / "orbits",
        )
        logger.info("Orbit for {}: {}", cfg.burst_id, orbit_path.name)

        # Stage 5: run_rtc + compare
        expected_cogs = [f"{cfg.burst_id}_VV.tif", f"{cfg.burst_id}_VH.tif"]
        if ensure_resume_safe(burst_out, expected_cogs):
            logger.info(
                "RTC output cached for {}; skipping run_rtc", cfg.burst_id
            )
            cog_paths = sorted(burst_out.glob("*.tif"))
        else:
            rtc_result = run_rtc(
                safe_paths=[safe_path],
                orbit_path=orbit_path,
                dem_path=dem_path,
                burst_ids=[cfg.burst_id],
                output_dir=burst_out,
            )
            if not rtc_result.valid:
                raise RuntimeError(
                    f"run_rtc failed for {cfg.burst_id}: "
                    f"{rtc_result.validation_errors}"
                )
            cog_paths = list(rtc_result.output_paths)

        # Compare VV polarisation (pick whichever COG matches VV).
        subsideo_vv = next(
            (p for p in cog_paths if "VV" in p.name), cog_paths[0]
        )
        cmp = compare_rtc(subsideo_vv, opera_vv)

        rmse_db = float(cmp.reference_agreement.measurements["rmse_db"])
        correlation = float(cmp.reference_agreement.measurements["correlation"])
        bias_db = float(cmp.reference_agreement.measurements["bias_db"])

        # D-13 investigation trigger
        inv_rmse_thresh = float(
            CRITERIA["rtc.eu.investigation_rmse_db_min"].threshold
        )
        inv_r_thresh = float(
            CRITERIA["rtc.eu.investigation_r_max"].threshold
        )
        reason_parts = []
        if rmse_db >= inv_rmse_thresh:
            reason_parts.append(
                f"RMSE {rmse_db:.3f} dB >= {inv_rmse_thresh:.2f} dB"
            )
        if correlation < inv_r_thresh:
            reason_parts.append(
                f"r {correlation:.4f} < {inv_r_thresh:.3f}"
            )
        investigation_required = bool(reason_parts)
        investigation_reason = (
            "; ".join(reason_parts) if reason_parts else None
        )

        # BINDING gate (RTC-02 frozen)
        rmse_pass = rmse_db < float(CRITERIA["rtc.rmse_db_max"].threshold)
        r_pass = correlation > float(CRITERIA["rtc.correlation_min"].threshold)
        status: Literal["PASS", "FAIL"] = (
            "PASS" if (rmse_pass and r_pass) else "FAIL"
        )

        return BurstResult(
            burst_id=cfg.burst_id,
            regime=cfg.regime,
            lat=cfg.centroid_lat,
            max_relief_m=compute_max_relief(dem_path),
            cached=cached,
            status=status,
            product_quality=None,  # no PQ gate for RTC in v1.1
            reference_agreement=ReferenceAgreementResultJson(
                measurements={
                    "rmse_db": rmse_db,
                    "correlation": correlation,
                    "bias_db": bias_db,
                },
                criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
            ),
            investigation_required=investigation_required,
            investigation_reason=investigation_reason,
            error=None,
            traceback=None,
        )


    # -- Main loop -------------------------------------------------------

    per_burst: list[BurstResult] = []
    per_burst_input_hashes: dict[str, dict[str, str]] = {}
    for cfg in BURSTS:
        t0 = time.time()
        try:
            row = process_burst(cfg)
            per_burst.append(row)
            # Best-effort input hashing. Only hash files that actually exist
            # to keep the meta.json forward-compatible with failed bursts.
            inputs: dict[str, str] = {}
            dem_tifs_here = sorted(
                (CACHE / "dem" / cfg.burst_id).glob("*.tif")
            )
            opera_tifs_here = sorted(
                (CACHE / "opera_reference" / cfg.burst_id).glob("*.tif")
            )
            for p in dem_tifs_here[:1]:
                inputs[f"{cfg.burst_id}_dem_sha256"] = sha256_of_file(p)
            for p in opera_tifs_here[:1]:
                inputs[f"{cfg.burst_id}_opera_ref_sha256"] = sha256_of_file(p)
            per_burst_input_hashes[cfg.burst_id] = inputs
            logger.info(
                "Burst {} PASS in {:.0f}s", cfg.burst_id, time.time() - t0
            )
        except Exception as e:  # noqa: BLE001 - per-burst isolation (D-06)
            tb = traceback.format_exc()
            logger.error(
                "Burst {} FAIL ({:.0f}s): {}",
                cfg.burst_id, time.time() - t0, e,
            )
            per_burst.append(
                BurstResult(
                    burst_id=cfg.burst_id,
                    regime=cfg.regime,
                    lat=cfg.centroid_lat,
                    max_relief_m=None,
                    cached=False,
                    status="FAIL",
                    product_quality=None,
                    reference_agreement=ReferenceAgreementResultJson(
                        measurements={}, criterion_ids=[]
                    ),
                    investigation_required=False,
                    investigation_reason=None,
                    error=repr(e),
                    traceback=tb,
                )
            )


    # -- Aggregate + write metrics.json ----------------------------------

    pass_count = sum(1 for r in per_burst if r.status == "PASS")
    total = len(per_burst)
    any_investigation = any(r.investigation_required for r in per_burst)

    # worst_rmse / worst_r computed across PASS rows only (FAIL rows have
    # empty measurements).
    passed_rows = [r for r in per_burst if r.status == "PASS"]
    if passed_rows:
        worst = max(
            passed_rows,
            key=lambda r: float(
                r.reference_agreement.measurements.get("rmse_db", -1.0)
            ),
        )
        worst_rmse = float(worst.reference_agreement.measurements["rmse_db"])
        worst_r = float(
            min(
                passed_rows,
                key=lambda r: float(
                    r.reference_agreement.measurements.get("correlation", 2.0)
                ),
            ).reference_agreement.measurements["correlation"]
        )
        worst_burst_id = worst.burst_id
    else:
        worst_rmse = -1.0
        worst_r = -1.0
        worst_burst_id = "(none)"

    # Top-level reference_agreement (inherited from MetricsJson). Schema
    # restricts this to dict[str, float] -- numeric worst-case only; the
    # companion worst_burst_id lives in reference_agreement_aggregate below.
    aggregate_ra = ReferenceAgreementResultJson(
        measurements={
            "worst_rmse_db": worst_rmse,
            "worst_correlation": worst_r,
        },
        criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
    )

    metrics = RTCEUCellMetrics(
        product_quality=ProductQualityResultJson(
            measurements={}, criterion_ids=[]
        ),
        reference_agreement=aggregate_ra,
        criterion_ids_applied=["rtc.rmse_db_max", "rtc.correlation_min"],
        pass_count=pass_count,
        total=total,
        all_pass=(pass_count == total),
        any_investigation_required=any_investigation,
        reference_agreement_aggregate={
            "worst_rmse_db": worst_rmse,
            "worst_r": worst_r,
            "worst_burst_id": worst_burst_id,
        },
        per_burst=per_burst,
    )

    metrics_path = CACHE / "metrics.json"
    metrics_path.write_text(metrics.model_dump_json(indent=2))
    logger.info("Wrote {}", metrics_path)

    # -- meta.json -------------------------------------------------------

    git_sha, git_dirty = get_git_sha()

    # Phase-1 MetaJson has a flat input_hashes dict; we serialise per-burst
    # hashes by prefixing keys with burst_id (D-12 nested flattened).
    flat_input_hashes: dict[str, str] = {}
    for _burst_id, kv in per_burst_input_hashes.items():
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

    # Summary banner
    print()
    print("=" * 70)
    print(
        f"eval-rtc-eu: {pass_count}/{total} PASS",
        ("[investigation]" if any_investigation else ""),
    )
    for row in per_burst:
        if row.status == "PASS":
            rmse = float(row.reference_agreement.measurements.get("rmse_db", -1.0))
            r = float(row.reference_agreement.measurements.get("correlation", -1.0))
            print(
                f"  [PASS] {row.burst_id:30s} {row.regime:14s} "
                f"rmse={rmse:.3f} dB r={r:.4f}"
                + (
                    f" INVESTIGATE ({row.investigation_reason})"
                    if row.investigation_required else ""
                )
            )
        else:
            print(
                f"  [FAIL] {row.burst_id:30s} {row.regime:14s} "
                f"error={row.error}"
            )
    print("=" * 70)

    # Exit non-zero if any burst failed so `make eval-rtc-eu` surfaces the failure.
    sys.exit(0 if pass_count == total else 1)
