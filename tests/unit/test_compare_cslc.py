"""Compatibility test entry point for compare_cslc EGMS diagnostics.

Phase 09 plan verification invokes this file name. The focused EGMS tests live
in ``test_compare_cslc_egms_l2a.py`` to preserve the existing test layout.
"""

from tests.unit.test_compare_cslc_egms_l2a import *  # noqa: F401,F403
