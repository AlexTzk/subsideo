"""Static-invariant tests for scripts/recalibrate_dswe_thresholds.py."""
from __future__ import annotations

from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "recalibrate_dswe_thresholds.py"
)


def test_script_exists() -> None:
    assert SCRIPT.exists()


def test_expected_wall_s_value() -> None:
    """CONTEXT D-24: EXPECTED_WALL_S = 21600 (6 hr cold path)."""
    src = SCRIPT.read_text()
    assert "EXPECTED_WALL_S = 21600" in src or "EXPECTED_WALL_S=21600" in src


def test_mp_configure_at_top() -> None:
    src = SCRIPT.read_text()
    assert "from subsideo._mp import configure_multiprocessing" in src
    assert "configure_multiprocessing()" in src


def test_credential_preflight_4_vars() -> None:
    src = SCRIPT.read_text()
    assert "CDSE_CLIENT_ID" in src
    assert "CDSE_CLIENT_SECRET" in src
    assert "CDSE_S3_ACCESS_KEY" in src
    assert "CDSE_S3_SECRET_KEY" in src


def test_grid_bounds() -> None:
    """CONTEXT D-04 + REQUIREMENTS DSWX-04: grid bounds verification."""
    src = SCRIPT.read_text()
    assert "0.08" in src and "0.20" in src and "0.005" in src
    assert "-0.10" in src or "-0.1" in src
    assert "-0.65" in src and "-0.35" in src and "0.02" in src
    assert "8400" in src  # GRIDPOINTS count assertion


def test_six_aois_with_balaton_held_out() -> None:
    """CONTEXT D-01 + DSWX-03: 5 fit-set + 1 Balaton held-out = 6 AOIs."""
    src = SCRIPT.read_text()
    assert "alcantara" in src
    assert "tagus" in src
    assert "vanern" in src
    assert "garda" in src
    assert "donana" in src
    assert "balaton" in src
    assert "held_out=True" in src


def test_stage_0_nam_regression_assert() -> None:
    """CONTEXT D-20: Stage 0 reads eval-dswx_nam/metrics.json + asserts gate."""
    src = SCRIPT.read_text()
    assert "eval-dswx_nam/metrics.json" in src
    assert "f1_below_regression_threshold" in src
    assert "investigation_resolved" in src


def test_edge_of_grid_sentinel() -> None:
    """CONTEXT D-08: edge-of-grid sentinel auto-FAIL -- W3 uses DswxEUCellMetrics."""
    src = SCRIPT.read_text()
    assert "edge_check" in src
    assert "at_edge" in src
    assert "BLOCKER" in src
    # W3 fix: BLOCKER write uses validated schema, not hand-rolled dict
    assert "DswxEUCellMetrics(" in src
    assert (
        "named_upgrade_path=\"grid expansion required\"" in src
        or "named_upgrade_path='grid expansion required'" in src
    )


def test_loocv_b1_fix_10_folds() -> None:
    """B1 fix: leave-one-pair-out across 10 fit-set pairs (5 AOIs x 2 seasons), NOT 12."""
    src = SCRIPT.read_text()
    # The script must enumerate 10 (aoi, season) pairs:
    assert (
        'fitset_pairs = [(aoi, season) for aoi in FIT_SET_AOIS for season in ("wet", "dry")]'
        in src
    )
    assert "len(fitset_pairs) == 10" in src
    # The fold loop should iterate the pairs:
    assert (
        "for left_out_idx, (left_out_aoi, left_out_season) in enumerate(fitset_pairs):" in src
    )
    # range(12) is forbidden:
    assert "range(12)" not in src
    # left_out_season is recorded in the LOOCVPerFold output:
    assert "left_out_season" in src


def test_loocv_gap_acceptance_gate() -> None:
    """DSWX-06 + CONTEXT D-14: LOO-CV gap >= 0.02 -> BLOCKER + exit non-zero (W3 schema)."""
    src = SCRIPT.read_text()
    assert "loocv_gap" in src
    assert "0.02" in src
    # W3 fix: BLOCKER write uses validated schema:
    assert "DswxEUCellMetrics(" in src
    assert (
        "named_upgrade_path=\"fit-set quality review\"" in src
        or "named_upgrade_path='fit-set quality review'" in src
    )


def test_joblib_loky_pattern() -> None:
    """CONTEXT D-06 + RESEARCH §joblib: joblib.Parallel(n_jobs=-1, backend='loky')."""
    src = SCRIPT.read_text()
    assert "from joblib import Parallel, delayed" in src
    assert "backend=\"loky\"" in src or "backend='loky'" in src


def test_pyarrow_parquet_pattern() -> None:
    """CONTEXT D-07: per-pair gridscores.parquet via pyarrow."""
    src = SCRIPT.read_text()
    assert "import pyarrow" in src
    assert "pq.write_table" in src
    assert "gridscores.parquet" in src


def test_stage_5_b3_explicit_aggregate() -> None:
    """B3 fix: Stage 5 has explicit aggregation code; no placeholder stub."""
    src = SCRIPT.read_text()
    # Marker constructs from the B3-explicit body:
    assert "mean_f1_per_grid = (" in src
    assert "groupby([\"WIGT\", \"AWGT\", \"PSWT2_MNDWI\"])" in src
    assert "joint_best_idx = mean_f1_per_grid[\"f1\"].idxmax()" in src


def test_stage_3_b4_compute_intermediates_explicit() -> None:
    """B4 fix: Stage 3 compute_intermediates body is explicit with promoted helpers."""
    src = SCRIPT.read_text()
    assert "_resolve_band_paths_from_safe" in src
    assert "_read_bands" in src
    assert "_apply_boa_offset_and_claverie" in src
    assert "_fetch_jrc_tile_for_bbox" in src or "_fetch_jrc_tile" in src
    assert "_reproject_jrc_to_s2_grid" in src
    # Forbid the placeholder phrase:
    assert "mirror run_dswx body" not in src


def test_stage_9_b3_balaton_explicit() -> None:
    """B3 fix: Stage 9 has explicit Balaton scoring; no placeholder stub."""
    src = SCRIPT.read_text()
    # Marker constructs from B3-explicit Balaton scoring:
    assert "balaton_thresholds = DSWEThresholds(" in src
    assert 'for season in ("wet", "dry"):' in src
    assert "balaton_f1 = float(np.nanmean(balaton_f1s))" in src


def test_stage_10_w1_sentinel_anchors() -> None:
    """W1 fix: Stage 10 uses sentinel-comment anchor slicing, not regex."""
    src = SCRIPT.read_text()
    assert "BEGIN_ANCHOR = \"# ╔═ THRESHOLDS_EU_BEGIN ═\"" in src
    assert "END_ANCHOR = \"# ╚═ THRESHOLDS_EU_END ═\"" in src
    assert "src.find(BEGIN_ANCHOR)" in src
    assert "src.find(END_ANCHOR)" in src
    assert "assert begin_idx > 0" in src
    assert "assert end_idx > begin_idx" in src
    # No regex-based rewrite:
    assert "re.compile" not in src or "pattern.sub(new_eu_block" not in src


def test_threshold_module_rewrite_provenance() -> None:
    """CONTEXT D-09..D-12: Stage 10 rewrites THRESHOLDS_EU with full provenance."""
    src = SCRIPT.read_text()
    assert "src/subsideo/products/dswx_thresholds.py" in src
    assert "THRESHOLDS_EU" in src
    assert "fit_set_hash" in src
    assert "held_out_balaton_f1" in src
    assert "loocv_gap" in src


def test_papermill_skipped_per_research() -> None:
    """RESEARCH §papermill ABSENT -- Stage 11 skipped."""
    src = SCRIPT.read_text()
    assert "papermill" in src.lower()
    assert "SKIPPED" in src or "skipped" in src.lower()
