# Pitfalls Research — v1.1 N.Am./EU Validation Parity & Scientific PASS

**Domain:** SAR/InSAR validation hardening layered on a working OPERA-equivalent pipeline — product-quality gates, reference-agreement sanity checks, DSWx threshold recalibration, release-matrix orchestration
**Researched:** 2026-04-20
**Confidence:** HIGH on metrics-vs-targets discipline, validation-adapter, orchestration, and fork-mode pitfalls (grounded in v1.0 session logs); MEDIUM on the coherence-on-stable-terrain and JRC-ground-truth pitfalls (backed by published accuracy assessments but not yet empirically verified on subsideo's stacks); LOW on one speculative isce3-minor-version diagnostic (see Pitfall M3).

**Scope statement:** This document covers pitfalls that are **new to v1.1** or that were **documented but baseline-only in v1.0** and become acute once scientific PASS gates are being enforced. The v1.0 PITFALLS.md covered install-layer, CDSE S3, EU burst DB, UTM zones, phase-unwrapping, ERA5, GLO-30, orbits, OPERA spec, EGMS methodology, macOS arm64, DSWx HLS-vs-L2A, and the four numpy-2/compass patches. Those pitfalls remain in force — this document does not repeat them.

**How to read this document:**

1. **Metrics-vs-targets discipline (M-series)** is the first-class category. BOOTSTRAP's central thesis ("once a metric becomes a target it stops being a metric") generates its own pitfall class. If you read nothing else, read this section.
2. **Phase-specific pitfalls (P-series)** are grouped by v1.1 phase (0 environment, 1 RTC EU, 2 CSLC self-consist, 3 DISP adapter, 4 DIST v0.1 + EFFIS, 5 DSWx recalibration, 6 release matrix).
3. **Orchestration and release-readiness pitfalls (R-series)** at the bottom cover `make eval-all`, reproducibility claims, and documentation drift.

Each pitfall has: what goes wrong, why it bites, warning signs, prevention strategy (code / process / artifact), target phase.

---

## Critical Pitfalls — Metrics-vs-Targets Discipline (M-series)

These are the pitfalls BOOTSTRAP's framing exists to prevent. They are the hardest to catch in review because the failure looks like "diligent engineering" — a team tightening criteria because they just demonstrated they can meet a tighter bar. Every pitfall in this section ends with a structural guardrail, not an "be careful" admonition, because "be careful" does not survive contact with a green CI run.

---

### Pitfall M1: Target-creep via reference-score anchoring

**What goes wrong:**
After a run produces r=0.79 vs OPERA CSLC amplitude (criterion r > 0.6), someone proposes "since we're clearly above the bar, we can tighten to r > 0.75 for next time." Next run lands at r=0.76, comfortably above the new bar. Two milestones later r > 0.85 seems reasonable because "we've been consistently around 0.79." Three milestones later a genuinely-better subsideo version that lands at r=0.71 fails the bar and gets flagged as a regression, even though it is arithmetically closer to OPERA amplitude than before on absolute terms. The reference's own cross-version-limited score has silently become the ceiling we chase rather than the floor we clear.

**Why it bites:**
Reference-agreement metrics compare subsideo output against OPERA/EGMS/JRC. They are bounded above by the reference's own accuracy — which at the cross-version level is knowably imperfect (see Pitfall 15 in v1.0 PITFALLS.md: phase coherence to OPERA CSLC is 0.0003 across isce3 0.15 → 0.25, amplitude r ≈ 0.79 is the practical ceiling). Tightening the bar toward the reference's score pretends this ceiling doesn't exist and forces subsideo to match artefacts of the reference's processing chain that may not be correct in an absolute sense.

**Warning signs:**
- A PR description that says "we landed at 0.79 last time so the 0.6 threshold is too loose"
- A CONCLUSIONS document whose "recommendations for next steps" section proposes tightening reference-agreement criteria based on a single data point
- Criterion constants (`R_THRESHOLD`, `RMSE_THRESHOLD`, etc.) that have been edited in the same commit that reports the new metric value
- Commit history on `src/subsideo/validation/compare_*.py` showing threshold changes clustered near validation session dates

**Prevention strategy (structural):**
- **Code-level:** Criterion constants live in a single immutable module (`src/subsideo/validation/criteria.py`) with a docstring documenting their derivation (cross-version isce3 phase limit for r > 0.6 amplitude; DSWE architectural ceiling for F1 > 0.90; etc.). Changing a constant requires a comment linking to either (a) an upstream algorithm change, (b) a ground-truth validation (e.g. CR network for RTC), or (c) an explicit ADR in `.planning/` justifying the change. No data-driven tightening allowed.
- **Process-level:** PR review checklist item: "does this PR change a criterion constant? If yes, is the justification (a) upstream algorithm, (b) ground-truth validation, (c) named ADR? Reference-score-based tightening is rejected at review."
- **Artifact-level:** The `results/matrix.md` generator must read criteria constants at runtime and print them alongside the measured value. This makes drift visible: an old matrix with `criterion: r > 0.6` next to a new matrix with `criterion: r > 0.75` is instantly flagged in git diff.

**Target phase:** Phase 0.5 (validation harness extraction). The `criteria.py` module and immutability convention is a harness-extraction deliverable. Every subsequent phase's compare_*.py consumers must import from it rather than defining locally.

---

### Pitfall M2: Conflation in reporting — reference-agreement and product-quality printed without structural separation

**What goes wrong:**
A CONCLUSIONS document or `results/matrix.md` entry writes "CSLC SoCal: r=0.79 PASS, coherence=0.73 PASS, residual=2.1 mm/yr PASS" on a single line. A reader (or a future LLM roadmap agent, or a downstream user, or the developer six months later) treats all three as equivalent PASS indicators. They are not — the first is a cross-version sanity check that cannot tighten, the second and third are product-quality gates. When the cross-version sanity check eventually drifts (say amplitude r drops to 0.68 because OPERA upgrades isce3 to 0.30 and the phase-screen logic changes again), the change is misread as a CSLC regression rather than a reference-side change, triggering unproductive investigation.

**Why it bites:**
BOOTSTRAP names this explicitly: "the two are reported separately and held to different standards." But the literal implementation of "reported separately" in matrix tables, CLI output, HTML reports, and CONCLUSIONS documents is not trivial. Without explicit separate columns, rows, or sections — and matching separate data structures in the code — the discipline is just a note in a PR description that gets lost on the next refactor.

**Warning signs:**
- A `ValidationResult` dataclass with a single `passed: bool` field and a single dict of metrics
- `results/matrix.md` with a single "Result" column rather than "Product-quality gate" and "Reference-agreement" as separate columns
- CLI output that prints "PASS" or "FAIL" without qualifying which criterion family produced the verdict
- HTML reports (Phase 7 of v1.0) where all metrics flow through the same `passed`/`failed` formatter

**Prevention strategy (structural):**
- **Code-level:** Split every `*ValidationResult` dataclass into two nested result objects: `product_quality: ProductQualityResult` and `reference_agreement: ReferenceAgreementResult`, each with their own `passed: bool` and metrics dict. `compare_*.py` functions return the composite object. No top-level `.passed` attribute that collapses the two.
- **Code-level:** The matrix generator (`make eval-all`) reads both nested objects and writes to two distinct columns: `Product-quality gate` and `Reference-agreement`. The cell text includes both the metric and the criterion (`coherence=0.73 > 0.7 PASS`), making the criterion source auditable at a glance.
- **Artifact-level:** `docs/validation_methodology.md` (Phase 6.2 deliverable) carries a fixed section titled "Product-quality gates vs reference-agreement sanity checks" with explicit per-product tables of which criterion is which. Every CONCLUSIONS document cross-references that doc when reporting a result.

**Target phase:** Phase 0.5 (harness), Phase 6.1 (matrix), Phase 6.2 (methodology doc). The three must land together — introducing the split dataclass without updating the matrix generator is worse than the current state (it adds complexity without the discipline benefit).

---

### Pitfall M3: Reference-agreement criterion silently used as a gate in CI

**What goes wrong:**
A developer adds a pytest assertion `assert result.amplitude_correlation > 0.6` to a regression test. Six months later they refactor compare_cslc.py and land on r=0.58 because of a minor interpolation change. The test fails. The fix is to regenerate the reference fixture and move on — except the reference fixture is OPERA v1.1 and the local change is methodologically sound. The test gets "fixed" by lowering the constant to 0.55, or by regenerating the expected value, not by investigating whether the drift is meaningful. Reference-agreement has become a gate despite BOOTSTRAP's explicit "does not tighten" framing.

**Why it bites:**
pytest assertions are a natural place to put threshold checks. But reference-agreement sanity checks are not gates — they are warnings that justify investigation, not automated pass/fail boundaries. Putting them in CI creates exactly the feedback loop BOOTSTRAP wants to avoid: CI failure → tighten-or-loosen threshold → silent drift.

**Warning signs:**
- Any assertion in `tests/` that compares a computed metric against a reference-agreement threshold from `criteria.py`
- Any `pytest.mark.validation` test that returns non-zero based on a reference-agreement number
- CI log output showing "tightening" or "relaxing" justifications in commit messages near test-constants changes

**Prevention strategy (structural):**
- **Code-level:** Reference-agreement tests in `tests/` assert only the *plumbing* — that metrics were computed, that the output shape is correct, that the reference was loaded — not the *values*. Criterion comparisons happen in eval scripts (`run_eval_*.py`), which write results to `results/matrix.md`, not in pytest assertions.
- **Code-level:** Product-quality gates *do* assert in tests (e.g. coherence > 0.7 on a golden-stable stack). The distinction is enforced by convention: the `tests/` directory has a `tests/product_quality/` subdirectory that contains asserting tests; `tests/reference_agreement/` has only no-assertion structural tests.
- **Artifact-level:** `.planning/research/PITFALLS.md` (this document, referenced in Phase 6.2) includes this pitfall by name so future contributors cannot say "we didn't know."

**Target phase:** Phase 0.5 (harness). Test directory structure decision lands with harness extraction. All Phase 1–5 eval scripts use this convention.

---

### Pitfall M4: Product-quality gate relaxation to clear a difficult-but-real FAIL

**What goes wrong:**
Phase 5 recalibrates DSWE thresholds, achieves F1 = 0.88 on EU (below the F1 > 0.90 bar). BOOTSTRAP's instruction is "FAIL with named ML upgrade path." A tempting alternative: "let's relax the bar to 0.85 because 0.88 is genuinely the best DSWE-family algorithms can do." This looks like pragmatism but it is the exact failure mode M1 describes applied to product-quality instead of reference-agreement. Once relaxed, the bar can only ever go further down — an honest FAIL with a named ML path is permanently lost as a signal.

**Why it bites:**
BOOTSTRAP §5.5 writes this out: "F1 > 0.90 is the bar. It does not move. Phase 5 reports exactly what F1 the recalibration achieves." But the social pressure during a milestone close-out to report PASS everywhere is real, and the temptation to argue "the bar was always aspirational" grows in proportion to how close to the bar we land.

**Warning signs:**
- A Phase 5 PR that edits the `F1_THRESHOLD` constant
- A CONCLUSIONS_DSWX_EU.md that reports F1=0.88 but frames it as PASS with a "revised criterion"
- Any discussion in retrospectives framing "moving the goalpost" as pragmatic

**Prevention strategy (structural):**
- **Code-level:** `criteria.py` has an immutable `DSWX_F1_THRESHOLD = 0.90` with a comment "DSWE-family architectural ceiling ≈ 0.92 per PROTEUS ATBD; moving this requires a new algorithm class (ML) and a new ADR." Modifying triggers PR review by whoever owns ADRs.
- **Process-level:** A FAIL outcome produces a named upgrade path. The matrix cell reads `F1 0.88 FAIL — ML-replacement upgrade path (see Future Work §DSWx)`. The FAIL is a first-class result, not a defect state to be fixed by relaxation.
- **Artifact-level:** BOOTSTRAP_V1.1.md §5.5 is quoted verbatim in `docs/validation_methodology.md` to make the commitment durable across milestone boundaries.

**Target phase:** Phase 5.5 (explicit in BOOTSTRAP). Guardrail lives in Phase 0.5 `criteria.py` and is enforced at Phase 6.1 matrix-generation time.

---

### Pitfall M5: "Product-quality gate" defined too tightly at first encounter

**What goes wrong:**
Phase 2 introduces the new "self-consistency coherence > 0.7 on stable terrain" product-quality gate. Absent any prior data, someone picks the threshold either by matching published stable-terrain coherence from C-band literature (often 0.8–0.9 on truly stable desert) or by running on a golden AOI and finding 0.82 and writing > 0.8. Either choice sets a tight bar that the three-AOI rollout (SoCal, Mojave, Meseta) then fails through no fault of subsideo — it's just variance in what "stable" means per AOI. The honest "FAIL with unknown cause" confuses the matrix.

**Why it bites:**
New product-quality gates have no prior data to calibrate against. The 0.7 threshold in BOOTSTRAP is a sensible starting bar but could itself be too high or too low by 0.1. Pre-committing tightly for the first rollout is exactly the "metric becomes a target" trap applied to product-quality.

**Warning signs:**
- A coherence threshold being chosen from literature rather than from a null-hypothesis distribution on synthetic or empirically-verified-stable data
- No explicit "tightening condition" paragraph in the CONCLUSIONS document introducing the new gate
- The 5 mm/yr residual velocity bar being applied to a 3-month stack without acknowledging it was set for 6 months

**Prevention strategy (structural):**
- **Process-level:** First rollout of a new product-quality gate is framed as "calibration run" in CONCLUSIONS. The gate has a *criterion* (0.7) but the first rollout result is not PASS/FAIL — it is "calibration data point: SoCal=0.XX, Mojave=0.XX, Meseta=0.XX." After 3+ data points, the gate becomes binding.
- **Code-level:** `criteria.py` distinguishes `CALIBRATING` vs `BINDING` criteria. The matrix generator marks `CALIBRATING` cells differently ("calibration: 0.73, target 0.7"). Only `BINDING` cells contribute to the PASS/FAIL verdict.
- **Process-level:** Tightening from 0.7 → 0.75 after calibration is allowed *only* if data from at least 3 geographies supports it. Loosening from 0.7 → 0.65 is equally allowed if the calibration proves 0.7 too tight for physical reasons. In both cases the change requires an ADR and a commit message documenting the reasoning.

**Target phase:** Phase 2 (CSLC self-consistency) introduces the first new product-quality gate; Phase 3 (DISP native-resolution self-consistency) and Phase 4 (DIST F1 > 0.80) reuse the calibration framing.

---

### Pitfall M6: CALIBRATING → BINDING transition drift ("it's still calibrating" forever)

**What goes wrong:**
The escape valve from M5 (the `CALIBRATING` label) can itself be abused: a gate that fails at three geographies stays marked `CALIBRATING` through v1.2, v1.3, never binds, and the pass/fail verdict silently relies on reference-agreement alone. "We need more data" can be a perpetual stall.

**Why it bites:**
Engineering calendars are infinite; pressure to close milestones is finite. "Calibrating" has no forcing function.

**Prevention strategy (structural):**
- **Code-level:** `criteria.py`'s `CALIBRATING` criteria carry an explicit `binding_after_milestone: str` field. A gate introduced in v1.1 Phase 2 says `binding_after_milestone: "v1.2"`. At v1.2 start, `make eval-all` refuses to run unless every `CALIBRATING` gate either (a) flips to `BINDING`, or (b) has an ADR documenting why the calibration window extends.
- **Process-level:** Milestone close-out checklist item: "review all CALIBRATING criteria; flip or justify."

**Target phase:** Phase 0.5 `criteria.py` design; Phase 6.1 matrix generator enforcement.

---

## Critical Pitfalls — Phase-Specific (P-series)

### P0.1: macOS fork mode introduces Cocoa / CFNetwork / FD-limit failures in dist-s1 and despeckling

**What goes wrong:**
BOOTSTRAP §0.4 prescribes `multiprocessing.set_start_method('fork')` on macOS to eliminate the `if __name__ == "__main__":` guard requirement and to avoid spawn-related deadlocks in dist-s1. Fork mode is faster and usually works — but has four known failure modes that will be triggered by the v1.1 workload:

1. **Cocoa / matplotlib:** importing matplotlib's default Agg backend before fork is safe; importing MacOSX backend (default in interactive shells) or pyplot at any point that initialises Cocoa is not. A parent process that has already plotted for a CLI progress display will fork children whose Cocoa state is invalid; the children segfault or deadlock at next graphics call.
2. **CFNetwork (HTTPS sockets):** macOS NSURLSession / CFNetwork connection pools are process-global and are corrupted by fork. Children that inherit a warm pool (e.g. from a requests.Session opened by the parent for CDSE downloads) will get `SSL_ERROR_ZERO_RETURN` or hang on first request.
3. **File descriptors > FD_SETSIZE (1024):** fork mode inherits all parent FDs. dist-s1 and dolphin both open many HDF5 files concurrently; a long-running parent (e.g. `make eval-all`) that has accumulated >1000 open FDs will fork children that immediately fail at FD-based `select()` calls.
4. **joblib/loky workers:** loky explicitly detects fork mode and emits deprecation warnings in Python ≥3.12; in Python 3.14 (and some backports) fork is being deprecated in favour of forkserver. loky's internal pool may fall back to spawn silently, defeating the fork intent.

Of these, **(2) and (3) will bite subsideo hardest**: the CDSE downloader in the harness warms a session for auth; dist-s1 chip processing opens many RTC COGs.

**Why it bites:**
BOOTSTRAP §0.4's "force fork" is correct for the dist-s1 hang it was written against, but insufficient as a universal fix. The risk is that the developer who implements §0.4 marks it resolved after three clean runs of `run_eval_dist.py`, then is bitten later by `make eval-all` (which runs dist-s1 *after* other eval scripts have warmed network pools).

**Warning signs:**
- `SSL: ZERO_RETURN` or socket hang after the first eval stage completes in `make eval-all`
- `OSError: [Errno 24] Too many open files` during dist-s1 chip processing after a long parent run
- joblib DeprecationWarning about fork/threaded usage in log output
- Deadlock only reproduced in the full matrix, not in the single `run_eval_dist.py` script
- `ulimit -n` returning 256 or 1024 (macOS default)

**Prevention strategy (structural):**
- **Code-level:** `src/subsideo/_mp.py::_configure_multiprocessing()` does more than set the start method. It also (a) raises `ulimit -n` to 4096 (macOS default is 256; run `resource.setrlimit(RLIMIT_NOFILE, ...)`), (b) sets `MPLBACKEND=Agg` in `os.environ` before any matplotlib import, (c) closes any module-global requests.Session that has been cached before forking children, and (d) refuses to set fork if `sys.version_info >= (3, 14)` and instead uses `forkserver`.
- **Code-level (watchdog):** The watchdog is process-level (not thread-level or signal-based). A `subprocess.Popen` wraps each eval stage; the parent monitors wall clock; at 2× expected + 0 throughput (measured by output-dir mtime) the parent sends SIGTERM, then SIGKILL after 30s grace. Thread-level watchdogs leak on fork; signal-based watchdogs are fragile under multi-threaded C extensions (isce3, GDAL).
- **Code-level:** `make eval-all` runs each eval as a subprocess, not inline. Each subprocess gets a fresh network pool, fresh FD table, fresh matplotlib state. This is slightly slower but eliminates cross-eval contamination.
- **Process-level:** Phase 0.4's acceptance criterion extends from "three consecutive fresh dist runs succeed" to "`make eval-all` from cold env succeeds three consecutive times on macOS M3 Max AND on Linux TrueNAS" (BOOTSTRAP Phase 6.3 already requires this; the new test is running it three times consecutively).

**Target phase:** Phase 0.4 (multiprocessing), Phase 0.7 (Makefile subprocess isolation), Phase 6.3 (pre-release audit).

---

### P0.2: numpy<2 pin transitively breaks something nobody looked at

**What goes wrong:**
Phase 0.1 pins numpy<2 in `conda-env.yml`. The conda solver accepts. Tests pass. Six weeks later a user file-watches xarray and gets `AttributeError: 'numpy.int64' object has no attribute 'tolist'` or similar because a dependency upgraded to a release that requires numpy>=2 (shapely 2.1+, rasterio 1.5+, MintPy 1.7+ all have partial numpy 2 soft dependencies). The conda solver accepts the pin but downgrades those packages to unsupported older versions, and some code path only exercised in a milestone-close eval breaks.

**Why it bites:**
numpy<2 pin is the right short-term fix for the compass/s1reader/isce3 three-way incompatibility, but "conda solver accepted my pin" is not "no transitive breakage." The solver is optimising for constraint satisfaction, not for testing coverage.

**Warning signs:**
- `conda list` after the pin shows shapely 2.0.x rather than 2.1.x (without explicit pin)
- New pytest failures in modules unrelated to CSLC (e.g. `test_burst_db` failing on `shapely.ops.unary_union`)
- A CI matrix test on Linux passing while the same code fails on macOS arm64 because conda-forge has different build-pins per platform

**Prevention strategy (structural):**
- **Code-level:** After pinning numpy<2, run `pytest tests/unit/ tests/integration/` with `-n auto` on *both* Linux and macOS-arm64 in CI (BOOTSTRAP Risk Register lists this mitigation). Record the full `conda list` output as a build artifact.
- **Code-level:** `conda-env.yml` pins numpy<2 *and* documents a sunset condition at the top of the file ("remove when compass >= X.Y.Z, s1reader >= A.B.C, and isce3 >= P.Q.R — see Phase 0.1"). Phase 0.1's deliverable includes a dated `TODO_NUMPY2.md` with the upstream sunset triggers.
- **Process-level:** Milestone close-out runs `pip check` and `mamba list --explicit > env.lockfile.txt`; diff against previous milestone and review non-subsideo packages that downgraded.
- **Artifact-level:** The lockfile is committed to `env/` with the milestone tag, making future reproduction possible even if the upstream registry shifts.

**Target phase:** Phase 0.1 (numpy pin), Phase 6.3 (pre-release audit runs lockfile diff).

---

### P0.3: rio_cogeo centralised helper masks a genuine COG-invalidation bug

**What goes wrong:**
BOOTSTRAP §0.3 consolidates rio_cogeo imports behind `src/subsideo/_cog.py`. The helper exposes `cog_validate()`. The underlying bug from v1.0 (Pitfall §3.2 of CONCLUSIONS_DSWX: `inject_opera_metadata` pushing the main IFD past the 300-byte COG header threshold) is solved by re-translate-after-tag. If the helper wraps `cog_validate` to swallow the "offset of main IFD should be < 300" warning (for convenience or to suppress log noise) without *also* triggering the re-translate, newly-written COGs will silently degrade to non-COG GeoTIFFs. Downstream users loading them with `rio_cogeo` succeed; cloud-native streaming over HTTP-range falls back to whole-file reads (slow, expensive).

**Why it bites:**
rio_cogeo's `cog_validate` output distinguishes errors, warnings, and info. A naive helper may do `strict=False` and return `(True, errors, warnings)` ignoring warnings. The IFD-offset warning is a real COG-layout break, not a stylistic concern.

**Warning signs:**
- A downstream user reports slow tile reads from RTC/DSWx outputs
- `gdalinfo <file> | grep LAYOUT` returns nothing (COG layout metadata missing)
- Output COGs produced by subsideo are 10%+ larger than equivalent `rio_cogeo cogeo create` outputs

**Prevention strategy (structural):**
- **Code-level:** `_cog.py`'s `cog_validate()` returns a structured result with `is_valid: bool`, `errors: list`, `warnings: list`. Callers must inspect warnings explicitly. The helper never implicitly coerces warnings to pass.
- **Code-level:** `_cog.py` exposes a second function `ensure_valid_cog(path)` that validates and, if any IFD/layout warning is present, re-translates in place. All metadata-injection code paths in v1.1 use `ensure_valid_cog` post-tag.
- **Code-level:** Smoke test in `tests/product_quality/test_cog_validity.py` loads each output COG and asserts `is_valid=True` with zero warnings *after* metadata injection.

**Target phase:** Phase 0.3 (rio_cogeo centralisation). Phase 1 (RTC EU) and Phase 5 (DSWx) re-verify by running the smoke test on their outputs.

---

### P0.4: Validation harness's `download_reference_with_retry` retries a non-retryable 401 forever

**What goes wrong:**
BOOTSTRAP §0.5 generalises the CDSE exponential-backoff pattern to a shared harness function. The CDSE case is safe because OOM / 429 are transient. Earthdata 401 (expired token) is *not* transient — retrying just accumulates retries. Worse, Earthdata 403 (account disabled or wrong app permissions) is semantically distinct from 429 but may return an HTML body that the harness's regex-based marker detection misreads. OPERA CloudFront (Phase 4.1) has yet another failure mode: 403 on URL signature expiry, which *is* retryable with a fresh URL but not with the same URL.

**Why it bites:**
"Generalise retry pattern" is a one-line design statement. Implementing correctly requires a per-source taxonomy of which status codes and response bodies are retryable, idempotent, or permanent.

**Warning signs:**
- `download_reference_with_retry` logs N retry attempts all with 401 responses
- Wall-clock time on a `make eval-all` run dominated by a single stalled download
- The harness's backoff cap (300s) being hit repeatedly rather than once

**Prevention strategy (structural):**
- **Code-level:** `download_reference_with_retry(url, retries_by_source)` accepts a per-source retry policy: `CDSE={'retry_on': [429, 'OutOfMemoryError'], 'abort_on': [401, 403]}`, `Earthdata={'retry_on': [429, 503], 'abort_on': [401, 403, 404]}`, `CloudFront={'retry_on': [503, 'ExpiredToken'], 'abort_on': [401, 404], 'refresh_url_on': [403]}`. The function refuses to proceed without an explicit policy.
- **Code-level:** Abort responses raise `ReferenceDownloadError` with the source and status; the eval script decides whether to bubble up (single-product eval) or skip-with-warning (matrix).
- **Process-level:** Phase 4.1 explicitly tests the CloudFront URL-expiry path with a synthetic expired URL; this is a harness deliverable, not a Phase 4 deliverable.

**Target phase:** Phase 0.5 (harness extraction).

---

### P1.1: EU RTC burst selection biased toward already-cached geographies

**What goes wrong:**
Phase 1 probes 3–5 EU bursts. The starting list reuses Bologna (cached from DISP EGMS) and the Portuguese fire footprint (cached from DIST EU). If budget tightens, Alpine and Scandinavian candidates get cut because "Bologna and Portugal already have cached SAFEs — cheaper to run." The cheapness bias produces an EU reproducibility claim that doesn't test steep-relief DEM handling or high-latitude variable DEM grid spacing (v1.0 Pitfall 7) — two of the regions most likely to expose region-dependent bugs.

**Why it bites:**
BOOTSTRAP §1.1 lists the terrain regimes precisely to cover the bug surface area: Alpine for steep relief, Scandinavian for > 50°N GLO-30 grid oddities, Portuguese for fire footprint (cached), Bologna for temperate flat (cached), Iberian for arid. Cutting Alpine or Scandinavian under budget pressure silently reduces the claim from "EU-wide reproducibility" to "cached-AOI reproducibility."

**Warning signs:**
- CONCLUSIONS_RTC_EU.md listing 3 bursts all below 45°N
- Phase 1 wall-clock time < 0.5 days (suspiciously fast — probably cached-only)
- No data from a burst with > 1000 m relief

**Prevention strategy (structural):**
- **Process-level:** Phase 1 acceptance criterion is "at least one burst each from: > 1000 m relief, > 55°N, and cached/cheap." Three bursts minimum; the first two mandatory, the third fillable from cache.
- **Code-level:** The matrix generator surfaces per-burst latitude and max DEM elevation in the RTC:EU cell summary, making a too-narrow selection visible at a glance.
- **Artifact-level:** CONCLUSIONS_RTC_EU.md has a fixed "terrain-regime coverage" table with columns {burst_id, lat, max_relief_m, cached?}. Any regime with no entry is flagged as "not validated in v1.1."

**Target phase:** Phase 1.1 (burst probing), Phase 1.3 (pass criteria).

---

### P2.1: WorldCover class 60 + slope < 10° includes seasonally-unstable terrain (dunes, salt flats, agricultural fallow)

**What goes wrong:**
BOOTSTRAP §2 defines "stable terrain" as ESA WorldCover class 60 (bare/sparse vegetation) + slope < 10°. Class 60 has commission errors in three categories that are decidedly not phase-stable:

1. **Coastal and interior dunes** (Aeolian transport causes pixel-scale phase noise; coherence < 0.3 typical on 12-day Sentinel-1)
2. **Salt flats / playas** (hygroscopic surface moisture variation across the 12-day cycle produces phase shifts > 1 rad without any ground motion)
3. **Agricultural fallow in the semi-arid EU** (ploughed bare fields classified as class 60 until new growth starts; tillage signature decorrelates C-band)

The WorldCover v2.0 Product Validation Report notes class 60 "had high accuracy" globally but *in Europe*, where class 60 covers small areas, accuracy drops. The Iberian Meseta candidate (Phase 2.3) and Mojave fallback (Phase 2.2) both contain all three false-positive categories.

**Why it bites:**
The coherence > 0.7 gate is calculated as a mean over the stability mask. If 20% of the mask is dune/playa/fallow with coherence < 0.3, the mean is pulled down by ~0.08 — enough to fail the gate through a mask-definition problem rather than a subsideo problem.

**Warning signs:**
- Coherence histogram on the stable mask is bimodal (true-stable peak near 0.85, dune/playa peak near 0.25)
- Mojave stable mask coherence 0.6–0.65 (would pass at 0.7 on SoCal)
- Visual inspection of the stability mask overlays known dune/playa features

**Prevention strategy (structural):**
- **Code-level:** Stability mask construction in `subsideo.validation.stable_terrain` (new module for Phase 2) applies class-60 + slope-<10° *and* additional filters: (a) distance from coastline > 5 km (excludes coastal dunes), (b) exclude WorldCover class 200 (permanent water) buffer > 500 m (excludes playa margins), (c) optional per-AOI `exclude_mask: Path` for known-unstable features (e.g. Coso/Searles Valley interior playas).
- **Code-level:** Report coherence as *median* on the stable mask, not mean; median is robust to the bimodal contamination. Also report p25 and p75 — if p25 < 0.5, the mask is contaminated.
- **Process-level:** First-run on each AOI produces a "stability mask sanity check" artifact: coherence histogram + mask-over-optical-basemap PNG, reviewed before the gate result is considered meaningful. This is where Pitfall M5's CALIBRATING framing matters.
- **Process-level:** Mojave candidate selection rule in BOOTSTRAP §2.2 ("documented stability in the published InSAR literature") is operationalised: the selection must cite a specific published paper that mapped the AOI's interior stability and excluded playas/dunes.

**Target phase:** Phase 2.1 (SoCal reveals the calibration curve), Phase 2.2 (Mojave stresses the mask), Phase 2.3 (Meseta EU).

---

### P2.2: Mean coherence on truly-stable terrain is lower than the 0.7 gate suggests

**What goes wrong:**
The 0.7 coherence threshold assumes that stable-terrain pixels remain coherent across 14 sequential 12-day pairs. Published C-band Sentinel-1 coherence on desert bedrock (the tightest stability case) is typically:
- Single pair, desert bedrock: 0.85–0.95
- 14-pair sequential stack, mean per-pixel: 0.75–0.85 (decorrelation accumulates; temporal baseline is still 12 days but a single low-coherence event in the stack drops the per-pixel mean)
- 14-pair sequential stack, mean per-pixel, SoCal (not desert bedrock): 0.65–0.75 (Mediterranean vegetation regrowth contaminates)

Counting "pixels that remain coherent across all 14 pairs" (intersection of coherent-pixel masks) is typically 40–70% of stable-terrain candidates. The 0.7 gate, applied naively to *mean coherence of all stable pixels across all pairs*, can fail even on a scientifically-well-functioning chain.

**Why it bites:**
BOOTSTRAP §2 does not specify the exact reduction: is it mean-of-means, mean over pairs of median-per-pair, median over the 14-pair intersection mask? These produce different numbers and the choice must be made before the calibration run, not after.

**Warning signs:**
- Mean coherence on SoCal stable mask 0.55 while p75 > 0.85 (the distribution is long-tailed; the mean masks the real stable fraction)
- Gate fails on SoCal (cached, known-well-functioning stack) — this is a definitional problem, not a subsideo problem

**Prevention strategy (structural):**
- **Code-level:** The stability gate reports three numbers: (a) median per-pair coherence on the stable mask, (b) fraction of stable-mask pixels with coherence > 0.7 in at least 12 of 14 pairs ("persistently coherent fraction"), and (c) median coherence among persistently-coherent pixels. The BOOTSTRAP 0.7 gate is applied to (a), but (b) and (c) are reported alongside to contextualise. CALIBRATING period (M5) allows tuning the choice.
- **Process-level:** SoCal run is the first calibration point. If the gate fails there through definitional reasons, the methodology changes, not the gate threshold — i.e. we switch to "median of persistently-coherent pixels > 0.7" rather than "mean of stable mask > 0.7." This is a methodology change, not a target-creep move.

**Target phase:** Phase 2.1 (SoCal calibration), Phase 2.2/2.3 apply.

---

### P2.3: Phase referencing — mean coherence is self-referencing-safe; residual velocity is not

**What goes wrong:**
The question asked whether subsideo's chain needs an explicit reference-pixel choice for coherence-on-stable-terrain to be meaningful.

- **Coherence is self-referencing-safe.** Interferometric coherence γ is computed as a normalised cross-correlation of complex values within a boxcar window; it has no dependency on an absolute phase reference. Adding a constant phase offset to the entire scene does not change coherence at any pixel.
- **Residual mean velocity is NOT self-referencing-safe.** Velocity = unwrapped phase / (2π) × λ/2 / Δt. Any absolute phase ambiguity translates directly to a velocity offset. If subsideo's chain picks one reference-pixel choice and OPERA-CSLC-derived stable pixels (used for "residual mean velocity < 5 mm/yr") are localized in the burst at a different point than where subsideo's implicit reference-pixel sits, the residual velocity has a spatial-mean bias that isn't physical.

BOOTSTRAP §2 says "residual mean velocity < 5 mm/yr at EGMS L2a stable-reference PS points within the burst footprint." EGMS L2a publishes values *already referenced* to EGMS's chosen reference network. Our chain publishes values referenced to *our* chosen reference (or no explicit choice). Comparing the two without an intermediate reference-transfer step will show arbitrary bias that has nothing to do with algorithm quality.

**Why it bites:**
This is a validation-methodology bug masquerading as an algorithm problem. The "5 mm/yr" number cited in BOOTSTRAP is only meaningful if the reference frame alignment is explicit.

**Warning signs:**
- Residual mean velocity on stable terrain shows a spatially-uniform bias (all pixels shifted by the same amount; not a spatial pattern)
- The bias magnitude changes when the comparison sub-area changes, despite the chain output not changing
- Different AOIs produce wildly different residual biases (−12, +8, −3 mm/yr) on comparable stable terrain

**Prevention strategy (structural):**
- **Code-level:** Residual velocity comparison in `subsideo.validation.compare_velocity` requires an explicit reference-transfer step: subtract the median velocity on a "common stable PS set" (intersection of subsideo stable mask and EGMS/OPERA stable pixels) from both products before computing the residual. Document this step in `docs/validation_methodology.md` as a methodological choice.
- **Code-level:** Coherence gate (self-referencing-safe) requires no such step; it reads the coherence directly and does not compute residual velocity for that gate.
- **Artifact-level:** `docs/validation_methodology.md` includes a "Reference frame alignment" section explicitly, called out with Pitfall P2.3 as its motivation.

**Target phase:** Phase 2.1 (SoCal, since OPERA-CSLC stable pixels are the US reference), Phase 2.3 (EU, since EGMS PS are the EU reference), Phase 3.2 (DISP same methodology).

---

### P2.4: "This time we'll subtract everything" — re-attempting cross-version phase comparison

**What goes wrong:**
CONCLUSIONS_CSLC_N_AM.md §5.3 documented that removing carrier phase, flattening phase, and both together all produced coherence ≈ 0.002 (random). A new contributor, unfamiliar with §5, re-attempts the comparison with additional corrections: "remove carrier + flatten + topo phase + solid Earth tide + iono + azimuth FM rate variation + range bistatic correction". Each additional removal feels like progress because each is a plausible source of phase difference. None of them individually or combined restores coherence — and each attempt costs a half-day.

**Why it bites:**
The CONCLUSIONS finding is methodologically strong but operationally fragile: it documents what *was tried*, not *why no further attempts can possibly work*. Without the structural argument, future attempts look like extending the list.

The structural argument: between isce3 0.15 and 0.25, the SLC interpolation kernel itself (not just the phase-screen corrections applied on top) changed. Two CSLCs computed from the same SLC with different interpolation kernels produce *different absolute phase values* at every pixel. No amount of post-processing correction can recover this — the correction would have to be "regenerate the OPERA CSLC with isce3 0.25's kernel", at which point it is just re-running the pipeline.

**Warning signs:**
- A PR titled "CSLC phase comparison: additional corrections" touching compare_cslc.py
- A CONCLUSIONS rerun showing coherence improvements from 0.0003 → 0.0015 and interpreting this as progress (both are random noise)
- Comments referencing "subtract X + Y + Z" without citing the interpolation-kernel-change argument

**Prevention strategy (structural):**
- **Artifact-level:** `docs/validation_methodology.md` (Phase 6.2 deliverable, explicitly called out in BOOTSTRAP §2.4) makes the interpolation-kernel-change argument the *first* paragraph of the cross-version section, not a footnote. The list of tried-and-failed corrections is an appendix, not the lead.
- **Code-level:** `compare_cslc.py` header docstring references `docs/validation_methodology.md#cross-version-phase`. Adding a new phase-correction branch requires the PR description to address why the interpolation-kernel argument no longer holds.
- **Process-level:** New contributors onboarding to DISP/CSLC work read `docs/validation_methodology.md` before touching compare_*.py.

**Diagnostic experiments to confirm impossibility holds across minor-version pairs:**

The question asked what additional experiments exist to confirm this is not just a 0.15 → 0.25 issue but a general isce3-version issue (important because OPERA may rebuild on a newer isce3 in a v0.X → v1.0 transition). Options:

- **isce3 0.15.1 vs isce3 0.19.1 pair**: Build the same AOI with both versions within subsideo. 0.19 is the minimum version compass 0.5.6 supports (per v1.0 STACK.md). Expected outcome: coherence between 0.15 and 0.19 already near zero, confirming the break happened at or before 0.19. **Cost**: ~1 day (build env with isce3 0.19, rerun eval).
- **isce3 0.25.8 vs isce3 0.25.10 pair**: Two minor-version releases. Expected outcome: if the interpolation kernel is stable within a minor series, coherence should be near 1.0. **Cost**: ~0.5 days (both available on conda-forge as of 0.25.10 March 2025).
- **isce3 0.25.10 vs isce3 current-latest pair**: Whatever ships by v1.1 close-out. Expected outcome: likely high coherence if the kernel is stable through the 0.25 series, which gives subsideo a useful signal that *within the current series*, phase comparison is possible. **Cost**: ~0.5 days.

Running the 0.19 vs 0.25 experiment is the most useful because it establishes whether the break is a 0.15 quirk (one-off, OPERA will eventually update) or a 0.15–0.25 structural change (permanent, any OPERA update within that range cannot be compared). LOW confidence: I do not have empirical data on whether the interpolation kernel changed at a specific minor version between 0.15 and 0.25 — this would need verification by building and running.

**Target phase:** Phase 2.4 (methodology doc). The diagnostic experiments are optional enhancements, not milestone-blocking.

---

### P3.1: "Native resolution" comparison via centre-pixel downsampling loses velocity statistics

**What goes wrong:**
BOOTSTRAP §3.1 describes `prepare_for_reference(native_velocity, reference_grid)` for multilooking 5×10 m → 30 m. The naive implementation is "take the pixel at the reference-grid cell centre" — fast, but (a) loses sub-pixel alignment information, (b) introduces aliasing because 30 m cells in subsideo may not align with OPERA's 30 m cells (Pitfall 4 from v1.0 — zone-boundary AOIs), and (c) discards all N>1 native pixels per reference cell, so noise statistics that depend on averaging (velocity standard deviation) are wrong by a factor of √N.

For multilooking a velocity field (not an SLC, not an interferogram — a processed velocity map):
- **Block-mean** (average all native pixels inside each reference cell) preserves the central-limit-theorem velocity estimate but does *not* preserve noise statistics correctly if the native pixels are not independent (they usually aren't — dolphin's phase linking correlates neighbours).
- **Centre-pixel** (take the pixel at the reference-cell centre) preserves point-wise interpretation but discards N-1 pixels per cell.
- **Bilinear** (spatial interpolation onto the reference grid) smooths velocity — preserves velocity gradients but blurs discontinuities (fault lines, subsidence basin edges).
- **Gaussian** (convolution with σ matching the reference cell size) is the physically correct low-pass filter before resampling — preserves velocity statistics if σ is chosen to match the effective resolution of the reference.

For this use case (comparing to OPERA DISP which is processed on a 30 m grid from its own multilooked interferograms), the physically consistent choice is **Gaussian convolution with σ ≈ 0.5 × 30 m = 15 m, then nearest-neighbour sample onto the reference grid**. This matches the effective smoothing OPERA applied to its 30 m output.

**Why it bites:**
Picking the wrong resampler silently changes the reference-agreement r by ±0.05 and the bias by ±1 mm/yr. A FAIL reported with the wrong resampler is not an honest FAIL — it's a resampler-choice FAIL dressed up as an algorithm FAIL.

**Warning signs:**
- r differs by > 0.03 when switching between block-mean and bilinear on the same velocity field
- Velocity-histogram width on the downsampled subsideo output is larger than on the OPERA DISP reference (indicates centre-pixel without averaging)
- Visible Moiré patterns in the difference map (indicates aliasing from misalignment + nearest-neighbour)

**Prevention strategy (structural):**
- **Code-level:** `prepare_for_reference()` takes an explicit `method: Literal["gaussian", "block_mean", "bilinear", "nearest"]` argument with no default. The adapter refuses to run without explicit choice. BOOTSTRAP's milestone default is `"gaussian"` with σ = 0.5 × reference_spacing.
- **Code-level:** Before resampling, the adapter snaps the output grid to the reference grid (origin at a multiple of the reference spacing) to eliminate alignment artefacts. If the native grid origin is not a factor of the reference spacing, the adapter cross-pads native data rather than misaligning.
- **Code-level:** For EGMS L2a PS (point data, not a grid), the adapter uses *Gaussian-weighted sample at PS coordinates* rather than nearest-neighbour. Weight kernel σ = 15 m matches the 30 m grid Gaussian choice. Document this as a methodology choice — PS points inherit the 30 m-effective smoothing, which is a different quantity than "velocity at the PS coordinate from a 5×10 m field."
- **Artifact-level:** `docs/validation_methodology.md` section "DISP comparison-adapter design" states the choice and rationale.

**Target phase:** Phase 3.1 (adapter), Phase 3.3 (re-run).

---

### P3.2: "PHASS planar ramp" lumps multiple failure modes into one label

**What goes wrong:**
CONCLUSIONS_DISP_EGMS.md §4.3 and CONCLUSIONS_DISP_N_AM.md §5 both identify "PHASS planar ramp" as the FAIL root cause. BOOTSTRAP §3 repeats this attribution. Phase 3's "honest FAIL" relies on this attribution being correct. But a planar phase ramp can come from at least four sources, some of which PHASS did not cause:

1. **PHASS deramping pathology** (the named root cause) — PHASS minimises L1-norm residuals and can land on solutions with low residual but a global phase slope, particularly on stacks with limited coherent-pixel density.
2. **Uncorrected tropospheric gradient** — stratified water-vapour loading over a burst has wavelength ≫ burst footprint; residual after ERA5 correction appears as a planar ramp. Bologna's Po-plain footprint is particularly susceptible because warm-moist boundary-layer gradients span the 200 km × 40 km swath.
3. **Orbit-state-vector error** — Sentinel-1 POEORB is accurate to ~5 cm in along-track. A 5 cm along-track position error at Sentinel-1 incidence angle produces a ~1 rad phase ramp across a 200 km burst. RESORB (the fallback when POEORB is not available — Pitfall 8 in v1.0) is accurate to ~20 cm, producing a ~4 rad ramp.
4. **Ionospheric phase screen gradient** — low-latitude (< 40°N) C-band ionosphere is usually sub-radian across a burst, but mid-latitude summer afternoons can produce TEC gradients of 2–5 rad across the 200 km burst footprint. Sentinel-1 C-band is less affected than L-band but not immune at high solar activity.

BOOTSTRAP's claim "single root cause on both continents" is possibly correct (PHASS is the suspect) but un-verified. Confusing the label with the diagnosis means the follow-up DISP Unwrapper Selection milestone could pick an unwrapper that doesn't help if the actual problem is (2), (3), or (4).

**Why it bites:**
The follow-up milestone's scope ("PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback multilook") is specific to unwrapper changes. If the ramp is ERA5-residual or orbit-error, none of those interventions fix it.

**Warning signs:**
- The ramp magnitude varies by > 50% between adjacent 12-day pairs (ionospheric or tropospheric — varies with atmospheric state)
- The ramp direction is stable across the stack (pointing north-south in the same burst across all 14 pairs, say) — consistent with orbit error, not PHASS
- Bologna ramp is stronger in summer-afternoon epochs than morning epochs (tropospheric signature)

**Prevention strategy (structural):**
- **Code-level (Phase 3.3 diagnostic):** Before declaring "PHASS FAIL," run three diagnostic tests:
  (a) Fit a planar ramp to each of the 14 unwrapped interferograms. Report ramp magnitude and direction per epoch. If direction is random and magnitude is correlated with interferogram coherence, suspect PHASS; if direction is stable and magnitude is comparable across pairs, suspect orbit; if magnitude correlates with atmospheric state (epoch-to-epoch variance), suspect tropospheric.
  (b) Swap RESORB for POEORB on any epoch currently using RESORB (v1.0 Pitfall 8). If ramp magnitude drops, orbit contribution confirmed.
  (c) Re-run with ERA5 tropospheric correction enabled, if it currently is not; if ramp magnitude drops, tropospheric contribution confirmed.
- **Artifact-level:** CONCLUSIONS_DISP_*.md includes a "Ramp attribution" table with the three diagnostic results. Labelling as "PHASS FAIL" requires (a) direction random, (b) no POEORB improvement, (c) no ERA5 improvement.
- **Process-level:** DISP Unwrapper Selection follow-up milestone scoping brief (Phase 3.4 deliverable) explicitly reads the Ramp attribution table and adjusts its candidate list if the diagnosis is (2), (3), or (4) rather than (1).

**Target phase:** Phase 3.3 (diagnostic adds to re-run); Phase 3.4 (brief consumes diagnostic output).

---

### P4.1: OPERA v0.1 DIST pre-operational config drift extraction failure

**What goes wrong:**
BOOTSTRAP §4.1 requires extracting OPERA v0.1's production metadata from the sample HDF5 to check for material configuration deltas vs dist-s1 2.0.13. The config-drift gate blocks the comparison if deltas are found. But the metadata extraction depends on OPERA v0.1 writing the config as structured attributes — it may instead be embedded as JSON strings in `/science/SENTINEL1/identification/processingInformation/productionParameters`, or written to a sidecar XML, or partially missing (pre-operational products often have incomplete metadata).

Known config parameters that drift between dist-s1 versions and are relevant to F1:
- **`confirmation_count`** (alert promotion threshold; 2.0.13 default is 3; OPERA operational target is 4)
- **`pre_image_strategy`** (`"multi_window_anniversary"` in 2.0.13; OPERA internal may use `"single_window"`)
- **`post_date_buffer_days`** (2.0.13 default 5; v0.1 could be 1 per the upstream PR note in BOOTSTRAP Future Work — the default changed across 2.x minors)
- **`baseline_window_length_days`** (2.0.13 default 365; OPERA may tune per-biome)
- **`despeckle_filter_size`** and **`despeckle_num_looks`** (tune the TBPF despeckle)
- **`low_confidence_threshold`** and **`high_confidence_threshold`** (backscatter-change dB thresholds)

If any of these differ and the comparison is run anyway, the F1 number will be biased in a direction that's difficult to predict (tighter thresholds → higher precision, lower recall; longer baseline window → more stable noise estimate, possibly tighter thresholds).

**Why it bites:**
BOOTSTRAP §4.1 is correct that config drift invalidates the comparison. But the extraction step is non-trivial and may quietly fail or return partial metadata, leaving the gate with incomplete information. A PR that implements "check config drift" by reading a subset of attributes and finding "no drift detected" can easily be wrong because the subset didn't cover the parameter that actually differed.

**Warning signs:**
- Metadata extraction returns fewer than ~15 config parameters (OPERA operational products typically write 20+)
- The `confirmation_count` or `despeckle_*` parameters are absent from the extraction
- CONCLUSIONS_DIST_N_AM_LA.md reports "no drift detected" without listing the specific parameters compared

**Prevention strategy (structural):**
- **Code-level:** `subsideo.validation.dist_config_drift.extract_opera_metadata(opera_h5_path) -> dict` returns a dict of known keys with explicit `None` for unset keys (not KeyError). The comparison function `compare_config(opera_config, subsideo_config) -> DriftReport` reports missing keys as `MISSING_IN_OPERA` / `MISSING_IN_SUBSIDEO` explicitly rather than silently ignoring.
- **Code-level:** The drift-check gate requires *all 7 listed parameters* to be extractable from OPERA v0.1. If any is `MISSING_IN_OPERA`, the gate fails-open to "config drift possible, comparison deferred" rather than "no drift detected, proceed."
- **Artifact-level:** CONCLUSIONS_DIST_N_AM_LA.md publishes the full DriftReport table, listing every parameter and its value in each system. Readers can independently assess drift even if the automated gate's interpretation is disputed.

**Target phase:** Phase 4.1 (LA v0.1 comparison). The drift-check module lands in Phase 0.5 harness-extraction since it's reusable for future operational-OPERA comparison too.

---

### P4.2: Single-tile F1 variance is large; the 0.80 bar does not account for it

**What goes wrong:**
BOOTSTRAP §4.1 and §4.6 require F1 > 0.80 on a single-tile, single-date comparison (T11SLT, 2025-01-21). Binary-classification F1 variance on a single tile can be surprisingly high:
- Tile area: 109.8 × 109.8 km = ~12,000 km² at the MGRS tile size
- At ~10% positive class (LA fire footprints), effective sample size for F1 bootstrap is ~1.2M pixels
- But spatial autocorrelation reduces effective sample size to tens-of-thousands of effective-independent-samples
- F1 bootstrap standard error on a single-tile, ~10% positive class binary classification is typically 0.02–0.05

This means a "true F1 0.82" and a "true F1 0.78" will produce single-tile measurements that cross the 0.80 bar roughly half the time. A PASS at F1 = 0.81 and a FAIL at F1 = 0.79 are not statistically distinguishable from a single tile.

**Why it bites:**
BOOTSTRAP correctly frames this as "single-observation snapshot, not a multi-observation confirmation test" (§4.1 caveat 3), but the F1 > 0.80 bar is still applied as a hard threshold. In a Bayesian sense this is fine (the best estimate on one tile is the MLE, no tighter uncertainty available), but the matrix cell should communicate the uncertainty rather than committing to PASS/FAIL as if the F1 were a true population parameter.

**Warning signs:**
- CONCLUSIONS_DIST_N_AM_LA.md reports F1 to 4 decimal places with no confidence interval
- Matrix cell reads `F1 0.81 PASS` with no margin qualifier
- A re-run on an adjacent tile (T11SLS, say) produces F1 = 0.78 and is interpreted as a regression rather than as variance

**Prevention strategy (structural):**
- **Code-level:** `compare_dist()` computes a bootstrap 95% CI on F1 by spatial block-resampling (blocks of 1 km × 1 km) with B=500 iterations. Returns `F1ResultWithCI(f1=..., ci_low=..., ci_high=..., n_effective=...)`.
- **Code-level:** The matrix cell formatter prints `F1 0.81 [0.77, 0.85] ~PASS` (wiggle-room indicator when the CI spans the threshold) or `F1 0.85 [0.83, 0.87] PASS` (clear pass).
- **Artifact-level:** `docs/validation_methodology.md` section on DIST explicitly notes the F1 uncertainty on single-tile comparisons and documents the bootstrap methodology.

**Target phase:** Phase 4.1 (LA v0.1), Phase 4.3 (EFFIS), Phase 4.4 (additional events).

---

### P4.3: CloudFront URL expiry and lack of Range support breaks resumable download

**What goes wrong:**
BOOTSTRAP §0.5 mentions "direct-download paths for non-CMR-indexed samples (e.g. OPERA CloudFront)" in the validation harness. CMR/Earthdata downloads are redirected to resumable CloudFront URLs with presigned query strings that typically expire after 1 hour. For a ~10 GB OPERA DIST v0.1 sample over a slow network, a 1-hour expiry may not be enough. Worse:

- CloudFront origin servers may not support HTTP Range requests for signed URLs (depends on distribution config)
- A failed download cannot be resumed — the partial file is useless, the URL must be regenerated (requires re-auth) and the full download re-tried
- CloudFront IP rotation mid-download causes TLS session drops on some clients

**Why it bites:**
The first `make eval-all` run that attempts the DIST v0.1 download on a slow network will time out, the user will retry, the URL will have expired, the auth flow will re-trigger, and the overall wall-clock explodes from the expected 10 minutes to hours of retry cycles — enough to make the `make eval-all` "< 12 hours" BOOTSTRAP 6.3 target fail.

**Warning signs:**
- `download_reference_with_retry` for the CloudFront URL reports 403 "SignatureExpired" after download starts
- Partial download files in `eval-dist/opera_reference/v0.1_T11SLT/` cache that never complete
- Range request attempts returning full-file responses (indicating server doesn't honour Range)

**Prevention strategy (structural):**
- **Code-level:** The CloudFront path in `download_reference_with_retry` pre-flights with a HEAD request, captures `Accept-Ranges: bytes`. If absent, the download is done in one shot with a long timeout; if present, chunked with resume support.
- **Code-level:** The URL is requested fresh before each chunk (or before retry) rather than cached — short URLs from CloudFront are presigned and cheap to regenerate.
- **Code-level:** Presigned URL generation (via OPERA's auth flow, if any; otherwise direct CloudFront with a known key) is isolated in a `get_opera_v01_url()` helper that can be called on demand.
- **Process-level:** The sample is ~1.5 GB per MGRS tile ("30 m, single-date, single-tile, LA fires" — per BOOTSTRAP §4.1 the sample is ~1 GB), within the 1-hour expiry budget on a typical broadband link. Phase 0.5 acceptance test includes a real CloudFront download from a similar distribution to verify the retry logic.

**Target phase:** Phase 0.5 (harness design), Phase 4.1 (LA v0.1 consumes it).

---

### P4.4: EFFIS perimeter rasterisation — `all_touched=True` vs `all_touched=False`

**What goes wrong:**
BOOTSTRAP §4.3 introduces EFFIS burnt-area polygons at 10–20 m as a same-resolution reference. Rasterising vector polygons to subsideo's 30 m DIST grid requires a choice:
- `all_touched=True`: mark every cell the polygon boundary passes through as burnt. Inflates the burnt-area count; produces commission errors at polygon edges.
- `all_touched=False` (the rasterio default): mark cells only if their centre falls inside the polygon. Underestimates narrow burnt fronts; produces omission errors at polygon edges.
- **Neither is correct for all cases.** A 30 m cell that is 50% burnt should arguably be burnt for recall purposes but unburnt for precision purposes — a cross-category ambiguity.

The difference in F1 between the two is typically 2–4 percentage points for a 10-m-resolution polygon rasterised to 30 m. This is larger than the gap between the 0.80 bar and typical subsideo DIST performance, meaning the raster-choice alone can flip the verdict.

**Why it bites:**
EFFIS's advertised "10–20 m resolution" is polygon-delineation accuracy, not pixel-grid posting. Rasterising to 30 m introduces resolution mismatch that must be handled explicitly.

**Warning signs:**
- Changing `all_touched` between runs produces F1 differences > 0.02
- The precision/recall tradeoff curve (varying the raster choice) goes through the 0.80 bar

**Prevention strategy (structural):**
- **Code-level:** `rasterize_effis()` always produces *two* rasters: a permissive (`all_touched=True`) and a conservative (`all_touched=False`) binary mask. `compare_dist()` reports F1 against both and takes the mean — or, more defensibly, reports F1-precision against the conservative mask and F1-recall against the permissive mask, then combines.
- **Code-level:** An alternative is fractional rasterisation (rasterio supports computing pixel coverage fractions via `rasterio.features.rasterize` with float output); the F1 is then computed on a continuous [0, 1] target with a binarization threshold. This is cleaner for polygon-on-edge handling but slower.
- **Artifact-level:** The rasterisation method is reported in CONCLUSIONS_DIST_EU.md alongside the F1. Different runs cannot use different rasterisations silently.

**Target phase:** Phase 4.3 (EFFIS comparison).

---

### P4.5: EFFIS "burnt" ≠ DIST-S1 "backscatter-change disturbed"

**What goes wrong:**
EFFIS delineates fire perimeters from optical dNBR (differenced Normalised Burn Ratio). Its "burnt" class includes:
- High-severity burn (all vegetation removed) — DIST-S1 detects easily
- Low-severity ground fire (canopy intact, understory burnt) — DIST-S1 may miss (backscatter change is subtle)
- Burn-and-resprout (fire 2–3 years prior with regrowth) — DIST-S1 may not flag (backscatter has recovered)
- Post-fire salvage logging — DIST-S1 detects as disturbance but EFFIS may or may not include in perimeter

Conversely, DIST-S1 "disturbed" includes:
- Clear-cut logging in unburnt forest — not in EFFIS perimeters
- Windthrow / storm damage — not in EFFIS
- Severe defoliation (insect, drought) — not in EFFIS
- Some false positives from soil moisture change in agricultural fields — not in EFFIS

The class-definition mismatch produces both false positives (DIST detects non-fire disturbance, EFFIS doesn't include) and false negatives (EFFIS includes low-severity burn that DIST can't detect from backscatter).

**Why it bites:**
BOOTSTRAP §4.3 sets "recall > 0.50, precision > 0.70" as pass criteria. Both numbers are reasonable given the class-definition mismatch, but interpreting a FAIL on either as a subsideo algorithm failure rather than a class-mismatch is the wrong call. The milestone should report two F1 flavors: (a) F1 against the EFFIS "high-severity" subset (if EFFIS publishes severity), (b) F1 against EFFIS all-classes.

**Warning signs:**
- Precision > 0.90 but recall 0.30 — likely a severity-class mismatch (subsideo only flags high-severity, which EFFIS also includes)
- Recall > 0.80 but precision 0.40 — likely a disturbance-vs-burn mismatch (subsideo over-flags)
- Inspection shows DIST disturbance clusters in agricultural fields adjacent to burnt areas (soil-moisture false positives)

**Prevention strategy (structural):**
- **Code-level:** If EFFIS publishes severity (usually as a `severity` attribute on the perimeter), the rasterisation separates severity classes. `compare_dist_vs_effis()` reports F1 against three subsets: all, high-severity-only, medium-or-higher.
- **Code-level:** A "disturbance attribution" sanity check post-F1: for false positives (DIST says disturbed, EFFIS says unburnt), check WorldCover class at the pixel. If > 50% are cropland (class 40), flag as likely agricultural-soil-moisture false positive; discount from the FAIL interpretation.
- **Artifact-level:** CONCLUSIONS section explicitly lists the class-definition mismatches; the F1 number is contextualised.

**Target phase:** Phase 4.3.

---

### P5.1: DSWE 3-parameter grid search overfits the 12-AOI fit set

**What goes wrong:**
BOOTSTRAP §5.3 grid-searches WIGT, AWGT, PSWT2_MNDWI on 12 (AOI, scene) pairs with Balaton held out. A 3-parameter joint search over the specified ranges has:
- WIGT: 24 steps
- AWGT: 20 steps
- PSWT2_MNDWI: 15 steps
- Grid total: 7200 combinations

With 12 fit-set pairs, each evaluation is ~1.2M pixels × 12 = 14M samples. The grid search is not large enough to massively overfit an independent-sample dataset of 14M, but the samples are spatially autocorrelated (effective N ≈ 1% of literal N = 140K) and the F1 landscape is known to be multimodal (DSWE has multiple local optima). The standard overfitting symptom:
- Fit-set mean F1 after recalibration: 0.91
- Balaton held-out F1: 0.85
- Train/test gap: 0.06 — indicates moderate overfitting

Without detecting overfit, the recalibration would be published as "F1 > 0.90 PASS" based on fit-set mean, when Balaton's 0.85 is the real number.

**Why it bites:**
"We used a held-out test set" is not by itself sufficient — the question is whether the held-out test set is *representative* of the fit-set. Balaton is one AOI; it could be an easy case or a hard case.

**Warning signs:**
- Fit-set F1 improves by > 0.02 vs default thresholds; held-out F1 improves by < 0.005
- Best-grid-point WIGT / AWGT / PSWT2_MNDWI values are at the edge of the search range (suggests grid too narrow)
- Best-grid-point values change by > 10% of range between independent random subsets of the 12-AOI fit set (cross-validated check)

**Prevention strategy (structural):**
- **Code-level:** The grid search reports *both* the fit-set mean F1 and a leave-one-out cross-validation mean F1 (fit on 11 AOIs, test on the 12th, rotated 12 times). If LOO-CV F1 is > 0.02 below fit-set F1, flag as overfit.
- **Code-level:** Balaton is held truly out until the recalibration is frozen. The final F1 on Balaton is the reported EU number, not the fit-set mean. If Balaton F1 < 0.90, report FAIL — not "fit-set F1 passed."
- **Process-level:** The grid-search script writes a `calibration_diagnostics.json` with the LOO-CV numbers, the grid-edge check, and the best-point stability across random subsets. Review this before accepting the new thresholds.

**Target phase:** Phase 5.3 (grid search), Phase 5.4 (re-run with fixed Balaton as test).

---

### P5.2: JRC Monthly History's own labelling errors contaminate the fit set

**What goes wrong:**
JRC Monthly History is published with documented commission accuracy 98–99% and omission accuracy 74–99% (with seasonal water pixels worst). Specific failure modes:
- **Land-in-shadow classified as water** (mountain shadow, deep urban canyon shadow, forest shadow at low sun angle). Iberian Meseta interior has low-relief so is mostly OK; Alpine valley AOIs will be contaminated.
- **Light clouds over water classified as land.** Atlantic estuary AOIs (Tagus, Shannon) in variable-weather months are particularly affected.
- **Shoreline pixels ambiguous.** JRC uses 30 m Landsat pixels; a pixel 50% water / 50% shore gets classified one way but the ground truth is mixed. For a DSWx algorithm evaluated at 30 m posting, shoreline pixel labels are the dominant F1 error source — they are neither "wrong" nor "right."

If the grid search fits thresholds to JRC's labelling errors (not to ground truth water/land), the resulting thresholds over-fit JRC's biases rather than improving DSWE.

**Why it bites:**
BOOTSTRAP §5.2 requires "JRC Monthly History reference quality over the candidate" as an AOI selection criterion but doesn't specify how to pre-screen. Without explicit QC, an AOI with 5% JRC mislabelling rate (common for forest-shadow-heavy Alpine valleys) silently contaminates the fit.

**Warning signs:**
- AOIs with > 20% JRC "unknown" class pixels (indicating sparse cloud-free observations)
- Confusion-matrix inspection shows many false negatives at shorelines or in cloud-adjacent areas
- F1 improvements on fit set concentrate at specific feature types (shorelines) rather than across-the-board

**Prevention strategy (structural):**
- **Code-level:** Pre-screen the fit set by computing `jrc_confidence(tile)` — fraction of pixels with < 5 cloud-free observations in the JRC time series. AOIs with > 5% low-confidence pixels are dropped from the fit set or replaced.
- **Code-level:** The grid search excludes shoreline pixels (1-pixel buffer around the JRC water/land boundary) from the F1 computation. Shoreline handling is a separate DSWE problem that threshold tuning can't resolve.
- **Process-level:** Phase 5.2 AOI selection explicitly mentions the pre-screen and the shoreline-exclusion choice; the exclusion is reported in CONCLUSIONS_DSWX_EU.md so downstream users know the F1 is a "non-shoreline F1."

**Target phase:** Phase 5.2 (fit set), Phase 5.3 (grid search).

---

### P5.3: DSWE F1 ceiling ≈ 0.92 is inherited without a citation chain

**What goes wrong:**
BOOTSTRAP §5 asserts "DSWE-family threshold algorithms have a documented architectural ceiling at F1 ≈ 0.92 globally." This is a load-bearing claim — it justifies the honest-FAIL outcome and the named ML upgrade path. But the claim's provenance in subsideo's docs is unclear: it came from OPERA DSWx-HLS ATBD / PROTEUS references, was carried forward in CONCLUSIONS_DSWX.md, and is now cited as an architectural fact in BOOTSTRAP.

If someone asks "show me the citation," the chain is:
- BOOTSTRAP → CONCLUSIONS_DSWX.md → OPERA DSWx-HLS ATBD → (further upstream, published F1 evaluation papers on DSWE)

Each hop is a possible point of drift. The 0.92 figure may be a rounded approximation from a specific evaluation with specific test conditions; the "global" qualifier may not survive the specific scope (e.g. it may be a N.Am. figure originally, not confirmed globally). If the v1.1 recalibration lands at F1 = 0.93 (beating the cited ceiling), the ceiling claim is demonstrably wrong and the FAIL framing for 0.88 was premature.

**Why it bites:**
An architectural ceiling claim is a strong statement that guides milestone framing. It must have an auditable source — not a game-of-telephone citation chain.

**Warning signs:**
- Nobody can produce a single published paper with "DSWE F1 ≈ 0.92 global ceiling" as a documented result
- CONCLUSIONS_DSWX.md cites the figure without a specific reference
- The figure is written with different levels of precision in different docs (0.92, ~0.9, 92%, ≈ 0.92)

**Prevention strategy (structural):**
- **Process-level:** Phase 5.5 Reporting has a prerequisite: verify the ceiling figure. Read the PROTEUS ATBD's validation section directly; extract the specific F1 reported (and against which reference, for which biome scope); cite specifically in `docs/validation_methodology.md`. If the specific number is 0.94 for a subset of biomes and 0.85 for another, report the range, not the ≈ 0.92 summary.
- **Artifact-level:** `docs/validation_methodology.md` has a "DSWE F1 ceiling" subsection with specific citations. If no published citation can be produced, the ceiling claim is softened to "empirically bounded by our 6-AOI evaluation at F1 ≈ 0.XX" (our own data, not a literature claim).
- **Code-level:** The criterion threshold in `criteria.py` is 0.90 (BOOTSTRAP's bar); the ceiling figure is a comment, not a criterion. This isolates the ceiling claim from the gate.

**Target phase:** Phase 5.5, Phase 6.2 (methodology doc).

---

### P5.4: Wet-vs-dry season scene pairing fails in drought years

**What goes wrong:**
Phase 5.2 specifies one wet-season and one dry-season cloud-free scene per AOI. Drought-year wet seasons (e.g. Iberian summer 2022, which had record-low rainfall) may have water extents indistinguishable from typical dry seasons. The "wet" scene for that AOI-year then provides very little signal for the threshold fit — both "wet" and "dry" scenes show similar water extents, so the pairing isn't stressing the algorithm.

Conversely, flood-year wet seasons over-represent flooded vegetation (JRC may class-3 label it; DSWE thresholds tuned for permanent water are inappropriate).

**Why it bites:**
The fit set size (12 pairs) is small. Two or three pairs undermining the wet-vs-dry spread due to drought or flood significantly reduces the effective calibration signal.

**Warning signs:**
- Wet-scene water area differs by < 10% from dry-scene water area for a given AOI
- Wet-scene is in a documented drought year (consult EU Drought Observatory for AOI year)
- JRC "seasonal water" class fraction in the AOI-month is much lower than the AOI's climatological norm

**Prevention strategy (structural):**
- **Process-level:** Phase 5.2 AOI selection includes a "wet-dry water extent ratio" check from JRC Monthly History climatology. If wet-month water extent is < 1.2× dry-month, the AOI-year pair is rejected and an alternate year is chosen.
- **Code-level:** The grid-search script reports per-AOI wet/dry F1 separately. If any AOI has near-identical wet/dry F1, flag as "low-information" and down-weight in the mean.

**Target phase:** Phase 5.2 (fit set construction).

---

## Orchestration and Release-Readiness Pitfalls (R-series)

### R1: `make eval-all` cache invalidation is under-specified

**What goes wrong:**
The cache hierarchy in v1.1 has many layers:
- Input SAFE files (CDSE S3, often 8 GB each)
- Orbits (POEORB/RESORB)
- DEM tiles
- EGMS reference CSVs
- OPERA reference HDF5/COG
- Intermediate CSLCs (40 GB per continent)
- DISP intermediate outputs
- Final eval result JSON / CONCLUSIONS markdown

A re-run of `make eval-all` may need to invalidate some layers and keep others. Cases:
- SAFE input bytes unchanged → skip re-download (file-size + SHA check)
- Eval script changed (new metric added, threshold changed) → re-run eval stages 7–9, keep stages 1–6
- `criteria.py` constant changed → re-run matrix generation only, not re-process
- dolphin or dist-s1 version changed → re-run all stages
- DEM bounds helper changed → re-download DEM if bounds changed, re-run geocoding

Without explicit cache-invalidation rules, `make eval-all` has two failure modes: too aggressive (always re-run everything, milestone close-out takes 12+ hours every time) or too lenient (stale cached results reported as fresh).

**Why it bites:**
"Re-run on warm env completes in seconds" (BOOTSTRAP 6.3 target) requires the lenient mode; "fresh clone → micromamba env create → make eval-all → filled matrix" (closure test) requires correctness. Both depend on precisely-defined cache invalidation.

**Warning signs:**
- `make eval-all` re-runs RTC even though the RTC eval script hasn't changed
- A CONCLUSIONS document timestamps mismatch the code git SHA at report time
- Matrix cell values differ between two consecutive `make eval-all` runs with no code changes

**Prevention strategy (structural):**
- **Code-level (Makefile):** Each eval target depends on specific files:
  ```
  eval-cslc-nam: run_eval_cslc.py src/subsideo/products/cslc.py src/subsideo/validation/criteria.py input/cached/socal.manifest
  ```
  Touch a file, invalidate its consumers. Use file-content hashes, not timestamps (git checkout resets timestamps).
- **Code-level:** Each eval script writes a `meta.json` sidecar with: input file hashes, script git SHA, criteria.py git SHA, Python / key-library versions. `make eval-all` compares meta.json to current state; re-runs only on mismatch.
- **Artifact-level:** `docs/validation_methodology.md` documents the cache invalidation rules so users can diagnose unexpected re-runs.

**Target phase:** Phase 0.7 (Makefile), Phase 6.1 (matrix).

---

### R2: Parallel eval execution shares download caches with concurrent-write risks

**What goes wrong:**
Single-developer workflow runs serial, but two-developer workflow and the pre-release audit (BOOTSTRAP 6.3) on TrueNAS with more cores will parallelise. Two eval scripts writing to the same DEM cache (`~/.subsideo/dem/`) or the same EGMS cache (`eval-disp-egms/egms_reference/`) concurrently will:
- Corrupt partial downloads (two processes opening the same destination file)
- Deadlock on SQLite burst-DB access (SQLite's file-locking semantics on shared NAS can be unreliable)
- Race on output-directory creation (`os.makedirs` with two processes both deciding to create the same directory)

**Why it bites:**
The Makefile parallel mode (`make -j4 eval-all`) is tempting for speed but requires explicit file-locking semantics across eval scripts. The single-developer workflow mask this.

**Warning signs:**
- Intermittent `FileExistsError` or `sqlite3.OperationalError: database is locked` in parallel runs
- Truncated SAFE files in cache
- Matrix cell randomly empty because the process crashed mid-run

**Prevention strategy (structural):**
- **Code-level:** Download helpers in `validation/harness.py` use `filelock.FileLock` on cache-directory-level locks. SQLite access uses WAL mode (`PRAGMA journal_mode=WAL`) for concurrent reads.
- **Code-level:** The Makefile declares a serial group for download-heavy stages and a parallel group for compute-heavy stages:
  ```
  .NOTPARALLEL: download-all
  eval-all: download-all eval-compute-all matrix
  eval-compute-all: eval-rtc eval-cslc eval-disp eval-dist eval-dswx  # parallelisable
  ```
- **Process-level:** Default `make eval-all` is serial; `make -j4 eval-all` is documented as "after download-all completes serially."

**Target phase:** Phase 0.7 (Makefile).

---

### R3: Failure isolation — one failing eval stages the matrix

**What goes wrong:**
If `eval-dist-nam` fails because CloudFront URL expired mid-download, `make eval-all` aborts and `results/matrix.md` is either not written or contains only the first few cells. The user sees "matrix generation failed" rather than "9 of 10 cells generated, 1 failed — here's the matrix with a clear FAIL for that cell."

**Why it bites:**
The milestone closure test requires `make eval-all` to produce a filled matrix on fresh environment. "Produce the matrix even when some cells failed" is the release-friendly behaviour; "abort on first failure" is the developer-friendly behaviour. Choose one deliberately.

**Warning signs:**
- `make eval-all` exits 1 on any per-eval failure, leaving `results/matrix.md` untouched
- Matrix file has mixed stale and fresh cells (worst case — partial write)

**Prevention strategy (structural):**
- **Code-level:** Each eval script writes its *own* result file (`results/cells/{product}_{region}.json`) and exits. The matrix generator reads all cell files at the end and writes `matrix.md`. A failing eval writes `results/cells/{product}_{region}.failed.json` with the error; the matrix generator marks the cell `RUN_FAILED — see results/cells/{product}_{region}.failed.json`.
- **Code-level:** `make eval-all` uses `-k` (keep going) mode by default for eval targets, so a failure doesn't abort the whole run. The final matrix target is not conditional on every eval succeeding — it always runs.
- **Code-level:** The matrix distinguishes three failure classes: `RUN_FAILED` (infrastructure), `FAIL_CRITERIA` (eval ran, didn't pass gate), `PASS`, and `DEFERRED`.

**Target phase:** Phase 0.7 (Makefile), Phase 6.1 (matrix).

---

### R4: Reproducibility-claim drift — the closure test is easy to claim, hard to verify

**What goes wrong:**
BOOTSTRAP milestone closure: "fresh clone → `micromamba env create -f conda-env.yml` → `make eval-all` → filled matrix." Claim is easy to write; verification requires a truly-fresh machine. In practice:
- The developer's local machine has a warm env (cached micromamba packages, cached CDSE SAFEs, warmed network pools). `make eval-all` "works in 10 minutes on my machine" is not equivalent to the closure test.
- CI typically runs with limited RAM/compute; the closure test (full matrix, 12 hours) may not fit in a CI budget.
- The TrueNAS audit (BOOTSTRAP 6.3) is a one-time check; subsequent drift between TrueNAS and the developer's machine is invisible until the next audit.

**Why it bites:**
Without continuous verification, the closure test becomes aspirational. A year after v1.1 ships, conda-forge package updates, CDSE API changes, or OPERA v0.1 URL migration can all break the closure test silently.

**Warning signs:**
- The closure test has been run once, documented in an audit report, and not since
- `conda-env.yml` has been modified without re-running the closure test
- Users reporting "I tried `make eval-all` and got X error" that the maintainer hasn't reproduced

**Prevention strategy (structural):**
- **Artifact-level:** A `Dockerfile` (or Apptainer recipe for HPC settings) reproduces the micromamba env + code clone. CI builds the image and runs `make eval-pytest` (unit tests only, not full eval) on every PR.
- **Artifact-level:** A monthly scheduled CI job runs the full closure test on a GitHub Actions large-runner (or self-hosted on TrueNAS). Failure emits a notification.
- **Artifact-level:** `conda-env.yml` is paired with a locked `env.lockfile.txt` (output of `mamba list --explicit`). The lockfile pins byte-exact package URLs; CI reproduces the lockfile to detect upstream drift.
- **Artifact-level:** Each milestone's retrospective includes an "audit date" field on the closure-test claim. If the audit date is > 30 days old, the claim is flagged for re-verification.

**Target phase:** Phase 6.3 (pre-release audit). CI config is a Phase 6 deliverable; lockfile commit is Phase 0.1 deliverable.

---

### R5: CONCLUSIONS docs vs `validation_methodology.md` drift

**What goes wrong:**
v1.0 accumulated 8 CONCLUSIONS files per product × session. v1.1 adds more (CONCLUSIONS_RTC_EU, CONCLUSIONS_CSLC_SELFCONSIST_NAM, CONCLUSIONS_CSLC_SELFCONSIST_MOJAVE, CONCLUSIONS_CSLC_EU, CONCLUSIONS_DIST_N_AM_LA, etc.). `docs/validation_methodology.md` is a Phase 6.2 deliverable that consolidates the methodological findings. Two failure modes:

1. **CONCLUSIONS treated as canonical.** The methodology doc becomes a derivative summary that goes stale as session-level findings evolve; users read both and find contradictions.
2. **Methodology doc treated as canonical but sessions keep their own methodology.** Each CONCLUSIONS adds a new methodology tweak that doesn't propagate back.

Neither is good. The milestone needs one canonical source and explicit derivation rules.

**Why it bites:**
CONCLUSIONS files are time-stamped session records; they are honestly "frozen at the date of the session." They should not be re-edited after that date. But the methodology they describe evolves. Without a canonical methodology doc that supersedes, new contributors may find the most-recent CONCLUSIONS and assume it's current.

**Prevention strategy (structural):**
- **Artifact-level:** `docs/validation_methodology.md` is canonical. Its top of file: "This document is canonical. When it conflicts with a CONCLUSIONS document, this document wins. CONCLUSIONS documents are session records and should not be edited after the session date." Every CONCLUSIONS file includes a header link to `validation_methodology.md`.
- **Process-level:** When a CONCLUSIONS introduces a new methodological finding, the same PR *also* updates `validation_methodology.md`. The PR checklist includes "methodology doc updated? If no, justify."
- **Process-level:** CONCLUSIONS files are immutable after date-of-session; subsequent findings go into new CONCLUSIONS or into `validation_methodology.md`, never edited back into the old one.

**Target phase:** Phase 6.2 (methodology doc creation).

---

## Technical Debt Patterns (v1.1-specific)

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip bootstrap CI on F1 (single-tile point estimate) | Faster eval | FAIL/PASS verdicts flip on single-tile variance | Never for matrix cells; OK for interactive debugging |
| Keep numpy monkey-patches instead of pinning numpy<2 | No conda solve changes | 4 patches documented in 2 places; drift risk | Only if pinning is empirically shown to break the env |
| Write a single `passed: bool` on ValidationResult | Simple API | Collapses product-quality and reference-agreement | Never |
| Use `all_touched=True` for EFFIS rasterisation without stating so | Higher recall | Silent inflation of burnt-area F1 | Never — report explicitly |
| Extract OPERA v0.1 config via best-effort dict traversal (no schema) | Fast implementation | Missed config drift, misleading PASS | Never — use explicit key list |
| Have the eval script compute F1 and assert > 0.80 in pytest | Reuses test infra | Reference-agreement becomes a CI gate (M3 violation) | Never — eval scripts write results, pytest tests the plumbing |
| Tighten criterion after a clean run ("we're above the bar") | Looks rigorous | Ratchets down over milestones, becomes unachievable | Never without an ADR citing algorithm change or ground truth |
| Use the fork start method blindly on macOS | Eliminates spawn guards | Cocoa / CFNetwork / FD-limit / loky failures | Only with the full mitigation bundle (MPLBACKEND, ulimit, closed sessions) |

---

## Integration Gotchas (v1.1-specific)

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OPERA CloudFront (DIST v0.1) | Caching the presigned URL | Regenerate URL per retry; check Accept-Ranges before resume |
| Earthdata (OPERA CSLC/DISP/DIST) | Retrying on 401 indefinitely | Per-source retry policy; 401/403 are abort, 429 is retry |
| EGMS portal | Reusing the `?id=<token>` across sessions | Token is search-session-bound; refresh per run |
| JRC Monthly History | Treating as ground truth | Pre-screen for shadow/cloud contamination; exclude shoreline buffer |
| EFFIS burnt-area polygons | Rasterising with rasterio defaults | Explicit `all_touched` choice; report both permissive and conservative F1 |
| ESA WorldCover class 60 | "Stable terrain = class 60 + slope < 10°" | Add 5 km coastline buffer, 500 m water buffer, optional AOI exclude mask |
| dist-s1 config drift vs OPERA v0.1 | Implicit default comparison | Explicit key list; MISSING_IN_OPERA fails drift-check gate |
| dolphin / dist-s1 multiprocessing on macOS | `set_start_method('fork')` standalone | Full bundle: fork + MPLBACKEND + ulimit + session close + joblib fork probe |
| pyaps3 vs CDS API (v2 format) | Assume 0.3.5 works | 0.3.6+ required since Feb 2025 CDS format change (v1.0 PITFALL noted; acute here because DISP ERA5 diagnostic is Phase 3.2 deliverable) |
| Makefile parallel execution | `make -j4 eval-all` out of the box | Download stages serial; compute stages parallel; file locks on shared caches |

---

## Performance Traps (v1.1-specific)

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Bootstrap CI with B=10000 on 1M-pixel F1 | F1 compute takes hours per eval | Block-bootstrap with B=500 and 1 km blocks; effective N is the bound | Every DIST / DSWx eval |
| `make eval-all` without cached SAFEs | 8-hour download time per fresh run | SAFE cache with SHA-based invalidation; pre-download in Makefile stage | Every fresh-env run |
| Full-resolution 5×10 m comparison adapter output written to disk | 20 GB per DISP eval; disk fills | Adapter streams to reference-grid-resolution output; intermediate in memory | DISP N.Am. + DISP EU |
| LOO-CV grid search on 12 AOIs × 7200 grid points | ~80 k runs; hours per recalibration | Cache scene classifications once; grid search re-scores, not re-processes | Phase 5.3 |
| Writing `meta.json` with full environment capture on every eval run | Disk bloat on repeated runs | Rotate meta.json; keep the most recent 10 | Long CI-run histories |

---

## Security Mistakes (v1.1-specific)

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing CDSE S3 access keys as lockfile artifacts | Credential leak if lockfile is public | Lockfile must be scrubbed of any URL containing credentials |
| Caching EGMS `?id=<token>` in `results/matrix.md` | Session token in git history | Strip download URLs from matrix output; log only file names |
| OPERA CloudFront signed-URL capture in `meta.json` | URL valid for 1 hour; low risk but not zero | Strip presigned query strings before writing meta |
| Running `make eval-all` in CI with credentials via env vars | Exposure via log lines | Mask env-var values in all log outputs; never `env | grep` in CI scripts |

---

## "Looks Done But Isn't" Checklist

- [ ] **Phase 0 numpy pin:** `conda-env.yml` pinned — verify with `mamba list | grep numpy` AND verify `pytest` passes on both Linux and macOS-arm64 (conda solver acceptance is not sufficient)
- [ ] **Phase 0 tophu dep:** Added to pip block — verify `from dolphin.unwrap import run` succeeds on a fresh env, not just on the developer's env
- [ ] **Phase 0 rio_cogeo helper:** `rg "from rio_cogeo" src/` returns only the helper — AND verify `_cog.ensure_valid_cog` re-translates post-metadata-injection (no 300-byte IFD warning)
- [ ] **Phase 0 mp helper:** `_configure_multiprocessing()` called in product entry points — AND sets MPLBACKEND, raises ulimit, closes cached Sessions; fork is not enough alone
- [ ] **Phase 0 harness:** Eval scripts import from `subsideo.validation.harness` — AND `download_reference_with_retry` uses per-source retry policies (CDSE, Earthdata, CloudFront each distinct)
- [ ] **Phase 0 DEM bounds:** No hand-coded bounds — AND the helper handles multi-zone AOIs (not just the SoCal single-zone case)
- [ ] **Phase 0 Makefile:** `make eval-all` runs — AND failure isolation works (one failing cell doesn't block matrix), AND cache invalidation correctly re-runs when criteria.py changes
- [ ] **Phase 1 RTC EU:** All bursts PASS — AND at least one is > 1000 m relief, AND at least one is > 55°N (regime coverage, not just cached)
- [ ] **Phase 2 CSLC self-consist:** Coherence > 0.7 reported — AND median/p25/p75 reported alongside, AND stability mask inspected for dune/playa contamination
- [ ] **Phase 2 residual velocity:** < 5 mm/yr reported — AND reference-frame-alignment step applied (subtract common-stable-set median)
- [ ] **Phase 2.4 methodology doc:** Cross-version phase section exists — AND leads with interpolation-kernel-change argument, not with "we tried X Y Z" list
- [ ] **Phase 3 comparison adapter:** `prepare_for_reference` works — AND takes explicit `method=` argument with no default, AND snaps grids to reference origin
- [ ] **Phase 3 ramp diagnostic:** FAIL reported — AND ramp-attribution table (random/orbit/tropospheric) populated before labelling as "PHASS"
- [ ] **Phase 4.1 DIST v0.1:** F1 reported — AND config-drift gate passed with explicit parameter list (all 7 keys extracted), AND bootstrap CI reported alongside point estimate
- [ ] **Phase 4.3 EFFIS:** F1 reported — AND both `all_touched=True` and `False` computed, AND severity-subset F1 where EFFIS publishes severity
- [ ] **Phase 5.3 recalibration:** Grid search completes — AND LOO-CV gap < 0.02, AND best-grid-point not at search-range edge, AND Balaton truly held out
- [ ] **Phase 5.5 criterion:** F1 > 0.90 bar UNCHANGED — AND DSWE ceiling citation resolved (specific paper or own-data fallback), AND criteria.py not edited to accommodate result
- [ ] **Phase 6.1 matrix:** `results/matrix.md` generated — AND separate product-quality and reference-agreement columns, AND CALIBRATING vs BINDING distinction surfaced
- [ ] **Phase 6.2 methodology doc:** Exists — AND canonical-over-CONCLUSIONS framing stated at top, AND linked from every CONCLUSIONS header
- [ ] **Phase 6.3 pre-release audit:** TrueNAS run passes — AND lockfile diffed against v1.0, AND Dockerfile / CI reproducer committed
- [ ] **Closure test:** "fresh clone → env create → make eval-all → matrix" claim — AND auditable via Dockerfile/CI, AND re-run date stamped, AND refresh in < 30 days before milestone close

---

## Recovery Strategies (v1.1-specific)

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Target-creep detected (M1) | MEDIUM | Revert criterion constant via git; re-run matrix; document in ADR; add review gate to prevent recurrence |
| Conflation in reporting (M2) | LOW | Restructure ValidationResult dataclass; re-run matrix generator (eval results cached) |
| Reference-agreement test in CI (M3) | LOW | Move assertion from pytest to eval script; CI passes; no re-compute needed |
| Product-quality relaxation attempt (M4) | LOW | Reject PR; enforce immutable criteria.py review gate |
| Fork-mode failure in matrix (P0.1) | MEDIUM | Verify MPLBACKEND/ulimit/session-close mitigations; re-run; if still failing on specific eval, isolate that eval as subprocess with env scrubbing |
| numpy<2 transitive breakage (P0.2) | MEDIUM | Diff `conda list` against v1.0 lockfile; identify downgraded package; add specific version pin; re-run tests |
| Stability mask contaminated (P2.1) | LOW | Apply coastline + water-buffer filters; re-run gate; re-report |
| Residual velocity reference-frame mismatch (P2.3) | LOW | Apply common-stable-set reference transfer; re-run compare; re-report |
| PHASS-mislabel (P3.2) | LOW | Run ramp-attribution diagnostic; update CONCLUSIONS labelling; may or may not change follow-up milestone scope |
| OPERA v0.1 config drift missed (P4.1) | LOW | Re-extract metadata with full key list; re-run drift gate; defer comparison if drift found |
| EFFIS rasterisation ambiguity (P4.4) | LOW | Report both all_touched=True and False; let reader interpret |
| DSWE grid search overfit (P5.1) | LOW-MEDIUM | Run LOO-CV; if gap > 0.02, expand fit set by 3–6 AOIs and re-run |
| JRC mislabelling contamination (P5.2) | LOW | Apply shoreline exclusion and confidence pre-screen; re-run grid search |
| Matrix cell stale (R1) | LOW | `make clean-cell-{product}-{region}` target forces re-run; matrix regenerates |
| Closure test aspiration drift (R4) | HIGH | Build Dockerfile + CI; schedule monthly re-run; budget 2 days to backfill after long drift |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| M1 Target-creep via reference-score anchoring | 0.5 (criteria.py), 6.1 (matrix) | `criteria.py` immutable per review gate; commit log of threshold changes empty over milestone |
| M2 Reporting conflation | 0.5, 6.1, 6.2 | Matrix has two columns; ValidationResult nested; CONCLUSIONS cross-link |
| M3 Reference-agreement in CI | 0.5 | `tests/` directory structure enforces split; no assertion on reference-agreement values |
| M4 Product-quality relaxation | 5.5, 0.5 (criteria.py) | F1 threshold unchanged; FAIL with upgrade path reported |
| M5 New-gate too-tight definition | 2.1 | First rollout framed as CALIBRATING; tightening requires 3 data points |
| M6 Perpetual CALIBRATING | 0.5 (criteria.py), 6.1 | `binding_after_milestone` field enforced at next milestone start |
| P0.1 macOS fork failures | 0.4, 0.7, 6.3 | Full mitigation bundle; 3 consecutive make eval-all runs pass |
| P0.2 numpy<2 transitive breakage | 0.1, 6.3 | Linux + macOS-arm64 tests; lockfile committed and diff'd |
| P0.3 rio_cogeo helper masking | 0.3 | `ensure_valid_cog` smoke test; zero-warning post-metadata assertion |
| P0.4 Retry policy | 0.5 | Per-source policy required; 401/403 abort verified |
| P1.1 EU RTC burst bias | 1.1 | Terrain-regime coverage table in CONCLUSIONS; > 1000 m relief burst included |
| P2.1 Stability mask contamination | 2.1 (SoCal reveals), 2.2, 2.3 | Coastline/water buffers applied; histogram inspected pre-gate |
| P2.2 Coherence-gate-definition | 2.1 | Median/p25/p75 reported; persistently-coherent fraction reported |
| P2.3 Reference-frame alignment | 2.1, 2.3, 3.2 | Common-stable-set transfer applied; documented in methodology |
| P2.4 Cross-version phase re-attempts | 2.4, 6.2 | Methodology doc leads with interpolation-kernel argument |
| P3.1 Multilook choice | 3.1 | Explicit `method=` argument; grid-snap before resample |
| P3.2 Ramp mis-attribution | 3.3, 3.4 | Ramp attribution table; follow-up brief consumes diagnostic |
| P4.1 Config-drift extraction | 4.1, 0.5 | Explicit 7-key list; MISSING fails drift gate |
| P4.2 F1 single-tile variance | 4.1, 4.3, 4.4 | Block-bootstrap CI reported; wiggle-room flag in matrix |
| P4.3 CloudFront URL expiry | 0.5, 4.1 | Accept-Ranges preflight; URL regen per retry |
| P4.4 EFFIS rasterisation | 4.3 | Both all_touched values reported |
| P4.5 EFFIS class mismatch | 4.3 | Severity subsets; agricultural FP attribution |
| P5.1 Grid-search overfit | 5.3 | LOO-CV gap < 0.02; Balaton truly held |
| P5.2 JRC mislabelling | 5.2 | Pre-screen applied; shoreline-exclusion F1 reported |
| P5.3 DSWE ceiling citation | 5.5, 6.2 | Specific citation resolved or fallback to own data |
| P5.4 Drought-year pairing | 5.2 | Wet/dry ratio check on fit set |
| R1 Cache invalidation | 0.7, 6.1 | `meta.json` per-eval; file-hash dependencies |
| R2 Parallel write races | 0.7 | File locks on cache; serial download stage |
| R3 Failure isolation | 0.7, 6.1 | Per-cell result files; matrix generator independent |
| R4 Reproducibility drift | 6.3 | Dockerfile / CI; monthly scheduled closure test |
| R5 CONCLUSIONS vs methodology drift | 6.2 | Canonical-over-session framing at methodology doc top; CONCLUSIONS header cross-link |

---

## Sources

- BOOTSTRAP_V1.1.md (local, definitive scope) — HIGH confidence for all phase-specific pitfalls
- CONCLUSIONS_CSLC_N_AM.md §5 (local) — HIGH confidence for cross-version phase impossibility (P2.4)
- CONCLUSIONS_DISP_N_AM.md §5 and CONCLUSIONS_DISP_EGMS.md §4.3 (local) — HIGH confidence for PHASS ramp signature (P3.2 baseline)
- CONCLUSIONS_DSWX.md §3 (local) — HIGH confidence for COG-metadata invalidation (P0.3)
- CONCLUSIONS_DIST_EU.md (local) — HIGH confidence for EMS cross-sensor precision-first framing (informs P4.5)
- v1.0 PITFALLS.md (baseline, not repeated here) — HIGH confidence for the install-layer, CDSE, ERA5, orbit, UTM, GLO-30, OPERA-spec, EGMS, and macOS-arm64 pitfalls that remain in force
- ESA WorldCover 2021 Product Validation Report v2.0 — MEDIUM confidence for class 60 regional-accuracy variation in Europe; https://worldcover2021.esa.int/data/docs/WorldCover_PVR_V2.0.pdf
- JRC Global Surface Water accuracy characterization — MEDIUM confidence for commission 98–99%, omission 74–99%, shadow-as-water and cloud-as-land failure modes; https://global-surface-water.appspot.com/
- joblib/loky fork-mode deprecation and macOS threading issues — MEDIUM confidence, reflects documented tracker issues; https://github.com/joblib/loky/issues/424, https://docs.python.org/3/library/multiprocessing.html (spawn default since 3.8; forkserver from 3.14)
- pythonspeed.com "Why your multiprocessing Pool is stuck" — MEDIUM confidence for fork+thread interaction; https://pythonspeed.com/articles/python-multiprocessing/
- rasterio.features.rasterize all_touched documentation — HIGH confidence for polygon-rasterisation tradeoff (P4.4)
- OPERA DSWx-HLS ATBD and PROTEUS validation (referenced but not fetched in this research pass) — LOW-MEDIUM confidence for the 0.92 ceiling claim; this is exactly the provenance question P5.3 raises

---

*Pitfalls research for: subsideo v1.1 — N.Am./EU Validation Parity & Scientific PASS milestone*
*Focus: metrics-vs-targets discipline as first-class category, plus phase-specific new pitfalls that arise when validation hardening is layered on a working v1.0 pipeline*
*Researched: 2026-04-20*
