# subsideo v1.2 Results Matrix

> **Version:** v1.2  
> **Date:** 2026-05-06  
> **Milestone:** v1.2 CSLC Binding & DISP Science Pass  
> **Status:** CLOSED — Phase 12 closure. DISP deferred to v1.3 (tophu/SNAPHU + orbital deramping). CSLC BINDING BLOCKER (Mojave + Iberian named blockers). All other cells unchanged from v1.1.

Manifest: `results/matrix_manifest.yml`

CALIBRATING cells are *italicised*. See `validation/criteria.py` for the 13-entry criterion registry; every measurement is echoed alongside its criterion's threshold (D-03 drift visibility).

| Product | Region | Product-quality | Reference-agreement |
|---------|--------|------------------|---------------------|
| RTC | NAM | — | DEFERRED — v1.2 N.Am. RTC re-run |
| RTC | EU | — | 3/5 PASS (2 FAIL) ⚠ |
| CSLC | NAM | BINDING BLOCKER / coh=0.80 / resid=1.1 mm/yr / blocker=required_aoi_binding_blocker (Mojave) ⚠ | amp_r=0.96 / amp_rmse=2.2 dB |
| CSLC | EU | BINDING BLOCKER / coh=0.86 / resid=0.4 mm/yr / blocker=required_aoi_binding_blocker (Iberian) ⚠ | amp_r=0.00 / amp_rmse=0.0 dB |
| DISP | NAM | DEFERRED — spurt:FAIL / deramp:retired / unblock=tophu-SNAPHU+orbital-deramping / interim=spurt-native(caveated) (see CONCLUSIONS_DISP_N_AM.md §Phase12) | 0.007 (> 0.92 FAIL) / 55.43 (< 3 FAIL) |
| DISP | EU | DEFERRED — spurt:FAIL / deramp:retired / unblock=tophu-SNAPHU+orbital-deramping / interim=spurt-native(caveated) (see CONCLUSIONS_DISP_EU.md §Phase12) | 0.3358 (> 0.92 FAIL) / 3.461 (< 3 FAIL) |
| DIST | NAM | — | DEFERRED (CMR: operational_not_found) |
| DIST | EU | — | 0/3 PASS (3 FAIL) \| worst f1=0.000 (aveiro) |
| DSWX | NAM | — | F1=0.925 PASS [aoi=Lake Tahoe (CA)] |
| DSWX | EU | — | F1=0.816 FAIL — named upgrade: fit-set quality review \| LOOCV gap=nan |
