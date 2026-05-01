# subsideo v1.1 Results Matrix

Manifest: `results/matrix_manifest.yml`

CALIBRATING cells are *italicised*. See `validation/criteria.py` for the 13-entry criterion registry; every measurement is echoed alongside its criterion's threshold (D-03 drift visibility).

| Product | Region | Product-quality | Reference-agreement |
|---------|--------|------------------|---------------------|
| RTC | NAM | — | DEFERRED — v1.2 N.Am. RTC re-run |
| RTC | EU | — | 3/5 PASS (2 FAIL) ⚠ |
| CSLC | NAM | BINDING BLOCKER / coh=0.80 / resid=1.1 mm/yr / blocker=required_aoi_binding_blocker (Mojave) ⚠ | amp_r=0.96 / amp_rmse=2.2 dB |
| CSLC | EU | BINDING BLOCKER / coh=0.86 / resid=0.4 mm/yr / blocker=required_aoi_binding_blocker (Iberian) ⚠ | amp_r=0.00 / amp_rmse=0.0 dB |
| DISP | NAM | *coh=0.89 ([phase3-cached]) / resid=-0.0 mm/yr / attr=inconclusive (CALIBRATING — needs 3rd AOI before binding; see DISP_UNWRAPPER_SELECTION_BRIEF.md)* | 0.04904 (> 0.92 FAIL) / 23.62 (< 3 FAIL) |
| DISP | EU | *coh=0.00 ([fresh]) / resid=+0.1 mm/yr / attr=inconclusive (CALIBRATING — needs 3rd AOI before binding; see DISP_UNWRAPPER_SELECTION_BRIEF.md)* | 0.3358 (> 0.92 FAIL) / 3.461 (< 3 FAIL) |
| DIST | NAM | — | DEFERRED (CMR: operational_not_found) |
| DIST | EU | — | 0/3 PASS (3 FAIL) \| worst f1=0.000 (aveiro) |
| DSWX | NAM | — | F1=0.925 PASS [aoi=Lake Tahoe (CA)] |
| DSWX | EU | — | F1=0.816 FAIL — named upgrade: fit-set quality review \| LOOCV gap=nan |
