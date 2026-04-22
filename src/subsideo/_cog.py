"""Version-aware wrapper around rio-cogeo 6.0.0.

Centralises every import of ``rio_cogeo`` so a future library upgrade is a
single-file change.  Surfaces ``cog_validate`` warnings explicitly -- the
IFD-offset-past-300-byte-header warning is a real COG-layout break, not a
stylistic concern (see .planning/research/PITFALLS.md Pitfall P0.3).

All ``rio_cogeo`` imports are deferred inside function bodies so
``pip install subsideo`` without the conda-forge stack still imports this
module cleanly.  Do NOT add ``import rio_cogeo`` at module top.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

_RIO_COGEO_VERSION: tuple[int, int, int] | None = None


def _get_version() -> tuple[int, int, int]:
    """Probe ``rio_cogeo.__version__`` once and cache the parsed tuple."""
    global _RIO_COGEO_VERSION
    if _RIO_COGEO_VERSION is None:
        import rio_cogeo

        parts = [int(p) for p in rio_cogeo.__version__.split(".")[:3]]
        parts += [0] * (3 - len(parts))
        _RIO_COGEO_VERSION = (parts[0], parts[1], parts[2])
    return _RIO_COGEO_VERSION


def RIO_COGEO_VERSION() -> tuple[int, int, int]:  # noqa: N802
    """Return the imported rio-cogeo (major, minor, patch) as ints."""
    return _get_version()


def cog_validate(path: str | Path) -> tuple[bool, list[str], list[str]]:
    """Return ``(is_valid, errors, warnings)`` for *path*.

    The third element (``warnings``) MUST be surfaced -- naive callers that
    only check ``is_valid`` will silently accept IFD-offset-past-header
    layout breaks (PITFALLS P0.3).

    rio-cogeo 6.0.0 signature::

        cog_validate(src_path, strict=False, config=None, quiet=False)
            -> Tuple[bool, List[str], List[str]]
    """
    from rio_cogeo.cogeo import cog_validate as _impl

    is_valid, errors, warnings = _impl(str(path), quiet=True)
    if warnings:
        logger.warning("rio_cogeo warnings for {}: {}", path, warnings)
    return is_valid, list(errors), list(warnings)


def cog_translate(
    src: str | Path,
    dst: str | Path,
    profile: Any,  # noqa: ANN401 -- rio_cogeo COGProfiles entry; typing lost to lazy import
    **kwargs: Any,  # noqa: ANN401 -- passthrough of rio_cogeo.cog_translate kwargs
) -> None:
    """Wrap ``rio_cogeo.cog_translate``.  Pass-through of the 6.0.0 API."""
    from rio_cogeo.cogeo import cog_translate as _impl

    _impl(str(src), str(dst), profile, **kwargs)


def cog_profiles() -> Any:  # noqa: ANN401 -- COGProfiles is rio_cogeo-internal; lazy-imported
    """Return ``rio_cogeo``'s ``cog_profiles`` registry (dict-like COGProfiles)."""
    from rio_cogeo.profiles import cog_profiles as _profiles

    return _profiles


def ensure_valid_cog(path: str | Path) -> None:
    """Validate *path*; if IFD-offset/layout warning is present, re-translate.

    Fixes PITFALLS P0.3 silent-COG-degradation.  All metadata-injection code
    paths (``products/rtc.py::ensure_cog``, ``products/dswx.py``, and
    ``_metadata.py::_inject_geotiff``) MUST call this AFTER their tag-write
    pass so the updated GeoTIFF is recertified as a valid COG.

    Raises
    ------
    RuntimeError
        If ``cog_validate`` reports structural errors (not just warnings).
    """
    path = Path(path)
    is_valid, errors, warnings = cog_validate(path)
    if errors:
        raise RuntimeError(f"{path} is not a valid COG: {errors}")
    ifd_bad = any(
        ("ifd" in w.lower() or "offset" in w.lower() or "layout" in w.lower())
        for w in warnings
    )
    if not ifd_bad:
        return
    logger.info("Re-translating {} to heal rio_cogeo warning: {}", path, warnings)
    tmp = path.with_suffix(path.suffix + ".cogtmp")
    profile = cog_profiles().get("deflate")
    cog_translate(
        src=str(path),
        dst=str(tmp),
        profile=profile,
        in_memory=False,
        quiet=True,
    )
    tmp.replace(path)
