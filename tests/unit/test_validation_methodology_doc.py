"""Regression guard for docs/validation_methodology.md structure + content.

Phase 3 Plan 03-05 CSLC-06 deliverable. Protects against:
  - Accidental deletion of the doc.
  - Addition of section 3/4/5 stub scaffolding (CONTEXT D-15 append-only
    policy -- only Phases 4/5/6/7 may add those sections with their own
    authoritative evidence).
  - Rearrangement that moves diagnostic-evidence appendix before the
    structural argument paragraph (PITFALLS P2.4 mitigation depends on
    that ordering).

Notes on filename discipline:
  The 03-05 plan frontmatter mentioned ``CONCLUSIONS_CSLC_EU.md`` but the
  EU CONCLUSIONS document was committed under the
  ``CONCLUSIONS_CSLC_SELFCONSIST_`` prefix to keep the naming symmetric
  with the N.Am. doc (``CONCLUSIONS_CSLC_SELFCONSIST_NAM.md``). These
  tests reference the real on-disk filenames and treat the plan name as
  a documented filename correction.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "docs" / "validation_methodology.md"
COMPARE_CSLC = REPO_ROOT / "src" / "subsideo" / "validation" / "compare_cslc.py"
CONCLUSIONS_NAM = REPO_ROOT / "CONCLUSIONS_CSLC_SELFCONSIST_NAM.md"
CONCLUSIONS_EU = REPO_ROOT / "CONCLUSIONS_CSLC_SELFCONSIST_EU.md"


def _read_doc() -> str:
    assert DOC.exists(), f"Missing {DOC}"
    return DOC.read_text()


def test_doc_exists_and_has_content() -> None:
    text = _read_doc()
    assert len(text.splitlines()) >= 120


def test_has_section_1_cslc_cross_version() -> None:
    text = _read_doc()
    assert "## 1. CSLC cross-version phase impossibility" in text


def test_has_section_2_product_quality_distinction() -> None:
    text = _read_doc()
    assert "## 2. Product-quality vs reference-agreement distinction" in text


def test_no_stub_scaffolding_for_phase_4_5_6_7() -> None:
    """D-15 append-only policy: section 3/4/5 belong to later phases."""
    text = _read_doc()
    for forbidden_header in ("## 3.", "## 4.", "## 5."):
        assert forbidden_header not in text, (
            f"Found stub-heading {forbidden_header!r} -- Phase 3 must NOT "
            "pre-create section 3/4/5. Phase 4 appends section 3; Phase "
            "5/6 append section 4/5; Phase 7 REL-03 writes the ToC."
        )


def test_structural_argument_leads_diagnostic_evidence() -> None:
    """P2.4 mitigation: the SLC interpolation kernel argument MUST lead.

    The diagnostic-evidence table (carrier/flattening -> coherence ~0.002)
    is an appendix, not the lead -- otherwise new contributors hit the
    table first and treat further corrections as "extend the list".
    """
    text = _read_doc()
    kernel_idx = text.find("SLC interpolation kernel")
    assert kernel_idx >= 0
    # Diagnostic sentinel: the 0.00x coherence numbers from CONCLUSIONS
    # CSLC_N_AM Section 5.3 (carrier/flattening -> coh 0.002).
    diag_idx = text.find("0.0003")
    if diag_idx < 0:
        diag_idx = text.find("0.002")
    assert diag_idx >= 0
    assert kernel_idx < diag_idx, (
        "Structural argument (SLC interpolation kernel) must precede "
        "diagnostic-evidence appendix (0.0003/0.002 coherence values). "
        "See PITFALLS P2.4 mitigation rule."
    )


def test_policy_statement_present() -> None:
    text = _read_doc()
    assert "Do NOT re-attempt with additional corrections" in text


def test_isce3_upstream_reference() -> None:
    text = _read_doc()
    assert "isce3" in text.lower()
    assert "github.com/isce-framework/isce3" in text, (
        "Missing upstream isce3 release-notes reference -- required by "
        "CONTEXT D-14 for the kernel-change structural argument."
    )


def test_section_2_motivating_example_cites_iberian() -> None:
    text = _read_doc()
    section_2 = text.split("## 2. Product-quality vs reference-agreement")[1]
    # The plan literal mentions CONCLUSIONS_CSLC_EU.md but the on-disk
    # filename is CONCLUSIONS_CSLC_SELFCONSIST_EU.md -- accept either.
    assert (
        "CONCLUSIONS_CSLC_EU.md" in section_2
        or "CONCLUSIONS_CSLC_SELFCONSIST_EU.md" in section_2
    ), (
        "Section 2 must cite the EU CSLC CONCLUSIONS doc by filename "
        "(SELFCONSIST_EU is the on-disk name)."
    )
    assert (
        "three independent numbers" in section_2
        or "three independent measurements" in section_2
    )


def test_section_2_anti_creep_both_directions() -> None:
    """Section 2 must cover M1 (reference-agreement not tightened) AND
    M4 (product-quality not relaxed)."""
    text = _read_doc().lower()
    assert "not tighten" in text or "must not be tightened" in text
    assert "not relax" in text or "must not be relaxed" in text


def test_compare_cslc_header_references_doc() -> None:
    """PITFALLS P2.4 code-level mitigation -- module header cross-links."""
    cslc_header = COMPARE_CSLC.read_text()[:2048]
    assert "docs/validation_methodology.md#cross-version-phase" in cslc_header


def test_conclusions_cross_links_retargeted() -> None:
    """Both CSLC CONCLUSIONS docs cross-link to the methodology doc and
    do NOT carry the ``Plan 03-05 pending`` placeholder text."""
    for doc in (CONCLUSIONS_NAM, CONCLUSIONS_EU):
        text = doc.read_text()
        assert "Plan 03-05 pending" not in text, f"{doc}: stale placeholder"
        assert "docs/validation_methodology.md" in text, (
            f"{doc}: missing methodology-doc cross-link"
        )


def test_no_orphan_todos_in_section_1_or_2() -> None:
    text = _read_doc()
    # Everything before section 3 (which is forbidden anyway). Use a
    # split that tolerates absence of any "## 3." header.
    s1_s2 = text.split("## 3.")[0]
    for token in ("TBD", "TODO", "STUB", "FIXME"):
        assert token not in s1_s2, (
            f"Section 1/2 contains {token!r} -- must be committed content."
        )
