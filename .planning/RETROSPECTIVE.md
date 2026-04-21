# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Initial Release

**Shipped:** 2026-04-09
**Phases:** 9 | **Plans:** 21 | **Tasks:** 39

### What Was Built
- Complete CDSE data access layer with OAuth2, STAC 1.1.0 search, and S3 download for Sentinel-1/2
- EU burst SQLite database from ESA GeoJSON extending opera-utils schema
- Five OPERA-equivalent product pipelines: RTC-S1, CSLC-S1, DISP-S1, DIST-S1, DSWx-S2
- Validation framework with comparison against OPERA N.Am., EGMS EU, and JRC GSW references
- Full Typer CLI (7 subcommands) with HTML/Markdown validation report generation
- 4,914 LOC source + 4,209 LOC tests across 88 files

### What Worked
- Lazy imports for conda-forge deps allowed pure-Python development and testing without the full conda stack
- Dataclasses over Pydantic for result types kept the product layer lightweight
- Phase 1 foundation investment paid off — all five product pipelines reused the same data access patterns
- Gap closure phases (5-9) caught real integration bugs that would have surfaced in production

### What Was Inefficient
- Phases 5-9 were all gap-closure/cleanup — 5 phases of fix-up for 4 phases of feature work suggests integration testing should happen earlier
- SUMMARY frontmatter metadata was inconsistently populated, requiring Phase 8 cleanup
- Report criteria key mismatches (Phase 9) could have been caught by stricter typing on the criteria dictionaries

### Patterns Established
- Lazy import pattern for all conda-forge-only deps (isce3, dolphin, tophu, etc.)
- `*_from_aoi()` pattern as the standard entry point for each product pipeline
- `inject_opera_metadata()` as shared utility across all product types
- Auto-fetch pattern for validation references (ASF for OPERA, EGMS for DISP)

### Key Lessons
1. Integration wiring between independently-developed phases needs explicit verification earlier — don't assume constructor signatures match
2. Two-layer install (conda + pip) works but requires lazy imports everywhere; document this prominently
3. Planning artifact metadata (SUMMARY frontmatter, ROADMAP progress) drifts during rapid development; automate checks

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 9 | 21 | First milestone; established lazy-import and from_aoi patterns |

### Cumulative Quality

| Milestone | Source LOC | Test LOC | Files | Commits |
|-----------|-----------|----------|-------|---------|
| v1.0 | 4,914 | 4,209 | 88 | 87 |

### Top Lessons (Verified Across Milestones)

1. Integration testing between phases should be built into the workflow, not deferred to cleanup phases
2. Lazy imports are essential for two-layer conda+pip installs — enforce this pattern from day one
