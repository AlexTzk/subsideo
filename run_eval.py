# run_eval.py — N.Am. RTC validation against OPERA
# Downloads S1 SLC from ASF (not CDSE — CDSE covers EU only)
import warnings; warnings.filterwarnings("ignore")

# Required on macOS: multiprocessing uses 'spawn', which re-imports this
# script in worker processes.  All top-level work must be inside this guard.
if __name__ == "__main__":
    import asf_search as asf
    import earthaccess
    from pathlib import Path
    from datetime import datetime
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.rtc import run_rtc
    from dotenv import load_dotenv
    load_dotenv()  # loads .env from the current working directory

    OUT = Path("./eval-rtc")
    BURST_ID = "t144_308029_iw1"   # lowercase for opera-rtc; 308029 is inside our downloaded SAFE
    SENSING_DATE = datetime(2024, 6, 24, 14, 1, 16)

    OUT.mkdir(exist_ok=True)

    auth = earthaccess.login(strategy="environment")  # uses EARTHDATA_* env vars

    # ── 1. Download OPERA reference product from ASF ─────────────────────────────
    print("Downloading OPERA reference...")
    ref_results = earthaccess.search_data(
        short_name="OPERA_L2_RTC-S1_V1",
        temporal=("2024-06-24", "2024-06-25"),
        granule_name="OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z*",
    )
    ref_dir = OUT / "opera_reference_308029"
    ref_dir.mkdir(exist_ok=True)
    # Skip if already downloaded
    if not any(ref_dir.glob("*.tif")):
        downloaded = earthaccess.download(ref_results, str(ref_dir))
        print(f"  Downloaded: {[Path(f).name for f in downloaded]}")
    else:
        print(f"  Already present: {[p.name for p in ref_dir.glob('*.tif')]}")

    # ── 2. Find matching S1 SLC from ASF ─────────────────────────────────────────
    # Relative orbit 144, S1A, sensing ~14:01 UTC 2024-06-24
    print("Searching ASF for source S1 SLC...")
    slc_results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel="SLC",
        beamMode="IW",
        relativeOrbit=144,
        start="2024-06-24T13:58:00Z",
        end="2024-06-24T14:05:00Z",
        maxResults=5,
    )
    if not slc_results:
        raise SystemExit("No S1 IW SLC found on ASF — check date/orbit")

    for r in slc_results:
        print(f"  {r.properties['fileID']}  {r.properties['startTime']}")

    # Pick the scene whose start time is closest to SENSING_DATE
    scene = min(slc_results, key=lambda r: abs(
        datetime.fromisoformat(r.properties["startTime"].rstrip("Z")) - SENSING_DATE
    ))
    print(f"Using: {scene.properties['fileID']}")

    # ── 3. Download DEM and orbit ─────────────────────────────────────────────────
    print("Fetching DEM and orbit...")
    dem_path, _ = fetch_dem(
        bounds=[-119.7, 33.2, -118.3, 34.0],  # t144_308029_iw1 footprint + 0.2° buffer
        output_epsg=32611,   # UTM zone 11N — Southern California
        output_dir=OUT / "dem",
    )
    orbit_path = fetch_orbit(
        sensing_time=SENSING_DATE,
        satellite="S1A",
        output_dir=OUT / "orbits",
    )
    print(f"  DEM:   {dem_path.name}")
    print(f"  Orbit: {orbit_path.name}")

    # ── 4. Download S1 SAFE from ASF ─────────────────────────────────────────────
    input_dir = OUT / "input"
    input_dir.mkdir(exist_ok=True)

    # asf_search downloads as <granule_name>.zip (no -SLC suffix)
    granule = scene.properties["fileID"].removesuffix("-SLC")
    safe_path = input_dir / f"{granule}.zip"

    if not safe_path.exists():
        print("Downloading S1 SAFE from ASF (~4 GB, takes a few minutes)...")
        session = asf.ASFSession().auth_with_creds(
            username=__import__("os").environ["EARTHDATA_USERNAME"],
            password=__import__("os").environ["EARTHDATA_PASSWORD"],
        )
        scene.download(path=str(input_dir), session=session)
        # find what was actually downloaded
        zips = sorted(input_dir.glob("*.zip"))
        safe_path = zips[-1]
        print(f"  SAFE: {safe_path.name} ({safe_path.stat().st_size / 1e9:.2f} GB)")
    else:
        print(f"  SAFE already present: {safe_path.name} ({safe_path.stat().st_size / 1e9:.2f} GB)")

    # ── 5. Run RTC pipeline ───────────────────────────────────────────────────────
    print("Running RTC pipeline...")
    result = run_rtc(
        safe_paths=[safe_path],
        orbit_path=orbit_path,
        dem_path=dem_path,
        burst_ids=[BURST_ID],
        output_dir=OUT / "output",
    )
    print(f"  Valid:  {result.valid}")
    print(f"  Errors: {result.validation_errors}")
    print(f"  COGs:   {[p.name for p in result.output_paths]}")
