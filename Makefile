# Makefile -- subsideo v1.1 eval orchestration (Phase 1 ENV-09 / D-12)
# Every eval-* target delegates to the Python supervisor so each cell runs
# as an isolated subprocess under the mtime-staleness watchdog. One failing
# cell does not stage the matrix (run `make -k eval-all` to continue past
# per-cell failures).

SHELL := /bin/bash
PY := micromamba run -n subsideo python
SUPERVISOR := $(PY) -m subsideo.validation.supervisor

.PHONY: eval-all eval-nam eval-eu results-matrix clean-cache help \
        eval-rtc-nam eval-rtc-eu eval-cslc-nam eval-cslc-eu \
        eval-disp-nam eval-disp-eu eval-dist-nam eval-dist-eu \
        eval-dswx-nam eval-dswx-eu

help:
	@echo "subsideo eval targets (per-cell subprocess isolation via supervisor):"
	@echo "  make eval-all              # all 10 cells (5 products x 2 regions)"
	@echo "  make eval-nam              # all 5 N.Am. cells"
	@echo "  make eval-eu               # all 5 EU cells"
	@echo "  make eval-<product>-<region>  # single cell, e.g. eval-rtc-nam"
	@echo "  make results-matrix        # regenerate results/matrix.md from sidecars"
	@echo "  make clean-cache FORCE=1   # remove all eval-*/ cache dirs"

# -- 10 matrix cells (5 products x 2 regions) --------------------------------
# N.Am. cells
eval-rtc-nam:   ; $(SUPERVISOR) run_eval.py
eval-rtc-eu:    ; $(SUPERVISOR) run_eval_rtc_eu.py
eval-cslc-nam:  ; $(SUPERVISOR) run_eval_cslc_selfconsist_nam.py
eval-cslc-eu:   ; $(SUPERVISOR) run_eval_cslc_selfconsist_eu.py
eval-disp-nam:  ; $(SUPERVISOR) run_eval_disp.py
eval-disp-eu:   ; $(SUPERVISOR) run_eval_disp_egms.py
eval-dist-nam:  ; $(SUPERVISOR) run_eval_dist.py
eval-dist-eu:   ; $(SUPERVISOR) run_eval_dist_eu.py
eval-dswx-nam:  ; $(SUPERVISOR) run_eval_dswx_nam.py
eval-dswx-eu:   ; $(SUPERVISOR) run_eval_dswx.py

# Note: run_eval_rtc_eu.py is a Phase 2 deliverable.
# run_eval_cslc_selfconsist_{nam,eu}.py are Phase 3 deliverables (supersede run_eval_cslc.py / run_eval_cslc_eu.py).
# run_eval_dswx_nam.py is a Phase 6 deliverable.
# Missing scripts fail-loudly; per-cell isolation (ENV-09) contains the failure.

eval-nam: eval-rtc-nam eval-cslc-nam eval-disp-nam eval-dist-nam eval-dswx-nam
eval-eu:  eval-rtc-eu  eval-cslc-eu  eval-disp-eu  eval-dist-eu  eval-dswx-eu

# `make -k eval-all` continues past per-cell failures (ENV-09 isolation).
eval-all: eval-nam eval-eu results-matrix

# results-matrix consumes sidecars produced by each eval-*/ cache; the
# matrix_writer module lands in Plan 01-08 (this target exists as the
# orchestration hook).
results-matrix:
	$(PY) -m subsideo.validation.matrix_writer --out results/matrix.md

# ----------------------------------------------------------------------------
# Phase 6 DSWx recalibration pipeline (DSWX-04 + DSWX-05)
# ----------------------------------------------------------------------------
# scripts/recalibrate_dswe_thresholds.py is a Phase 6 deliverable (Plan 06-06).
# Wired here in Plan 06-01 so Plan 06-06 can `make recalibrate-dswx` immediately
# without Makefile edits.
recalibrate-dswx:
	$(SUPERVISOR) scripts/recalibrate_dswe_thresholds.py
.PHONY: recalibrate-dswx

# ----------------------------------------------------------------------------
# Phase 6 docs auto-render: dswx_aoi_selection.ipynb -> dswx_fitset_aoi_selection.md
# ----------------------------------------------------------------------------
# Per CONTEXT D-01 + RESEARCH §Notebook rendering: keep the rendered docs copy
# in sync with the source notebook. nbconvert verified present in conda env.
docs/dswx_fitset_aoi_selection.md: notebooks/dswx_aoi_selection.ipynb
	micromamba run -n subsideo jupyter nbconvert --to markdown \
	    --output-dir docs \
	    --output dswx_fitset_aoi_selection.md \
	    notebooks/dswx_aoi_selection.ipynb

dswx-fitset-aoi-md: docs/dswx_fitset_aoi_selection.md
.PHONY: dswx-fitset-aoi-md

# Safety: require FORCE=1 to prevent accidental wipes (T-07-02 mitigation).
clean-cache:
ifeq ($(FORCE),1)
	@echo "Removing eval-*/ cache dirs..."
	rm -rf eval-*/
else
	@echo "Refusing to remove eval-*/ without FORCE=1. Run: make clean-cache FORCE=1"
	@exit 2
endif
