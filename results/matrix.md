# subsideo v1.1 Results Matrix

Manifest: `results/matrix_manifest.yml`

CALIBRATING cells are *italicised*. See `validation/criteria.py` for the 13-entry criterion registry; every measurement is echoed alongside its criterion's threshold (D-03 drift visibility).

| Product | Region | Product-quality | Reference-agreement |
|---------|--------|------------------|---------------------|
| RTC | NAM | RUN_FAILED (metrics.json missing) | RUN_FAILED |
| RTC | EU | — | 3/5 PASS (2 FAIL) ⚠ |
| CSLC | NAM | *2/2 CALIBRATING \| coh=0.80 / resid=1.1 mm/yr (Mojave)* | *amp_r=0.98 / amp_rmse=1.3 dB* |
| CSLC | EU | *1/1 CALIBRATING \| coh=0.87 / resid=0.0 mm/yr (Iberian)* | *amp_r=0.00 / amp_rmse=0.0 dB* |
| DISP | NAM | *coh=0.89 ([phase3-cached]) / resid=-0.0 mm/yr / attr=inconclusive (CALIBRATING)* | 0.04904 (> 0.92 FAIL) / 23.62 (< 3 FAIL) |
| DISP | EU | *coh=0.00 ([fresh]) / resid=+0.1 mm/yr / attr=inconclusive (CALIBRATING)* | 0.3358 (> 0.92 FAIL) / 3.461 (< 3 FAIL) |
| DIST | NAM | RUN_FAILED (metrics.json missing) | RUN_FAILED |
| DIST | EU | RUN_FAILED (metrics.json missing) | RUN_FAILED |
| DSWX | NAM | RUN_FAILED (metrics.json missing) | RUN_FAILED |
| DSWX | EU | RUN_FAILED (metrics.json missing) | RUN_FAILED |
