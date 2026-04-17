# find_scene.py
import warnings
warnings.filterwarnings("ignore")

import asf_search as asf
from opera_utils import get_burst_geodataframe
from shapely.geometry import box

# Small Southern California AOI
AOI = box(-118.5, 34.0, -118.0, 34.5)
WKT = AOI.wkt

# Find OPERA RTC products for this area
results = asf.search(
    platform=asf.PLATFORM.SENTINEL1,
    processingLevel="RTC",
    intersectsWith=WKT,
    start="2024-06-01",
    end="2024-07-01",
    maxResults=5,
)

print("=== OPERA RTC scenes ===")
for r in results:
    p = r.properties
    print(p["fileID"])
    print("  Date:", p["startTime"])
    print("  Burst:", p.get("operaBurstID"))
    print()

# Get burst IDs from opera-utils N.Am. DB
gdf = get_burst_geodataframe()
hits = gdf[gdf.geometry.intersects(AOI)]
burst_ids = hits["burst_id_jpl"].tolist()
print("=== Burst IDs for AOI ===")
for b in burst_ids[:10]:
    print(" ", b)
print(f"  ... ({len(burst_ids)} total)")
