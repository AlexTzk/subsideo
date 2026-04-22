# Dockerfile -- subsideo v1.1 reproducibility image (Phase 1 ENV-10 / D-17)
# CPU-only; multi-stage mambaorg/micromamba base.
#
# Critical conventions (per RESEARCH.md Pitfall 8):
#   - Keep USER=$MAMBA_USER throughout -- switching to the privileged
#     account breaks _entrypoint.sh env activation.
#   - Do NOT override ENTRYPOINT -- the base image's _entrypoint.sh
#     auto-activates the conda env before CMD runs.
#   - CPU-only image per D-17; no GPU runtime layer. dist-s1 GPU path
#     is M3-incompatible and not needed for closure tests.
#   - `mambaorg/micromamba:latest` tag is used for Phase 1 flexibility;
#     Open Question A7 notes Phase 7 may pin to a specific version tag.
#
# Env-name note (conda-env.yml `name: subsideo` vs `-n base` inside
# the image): host `micromamba env create -f conda-env.yml` creates an
# env literally named `subsideo`; inside the image we install the same
# package set into the pre-existing `base` env that mambaorg/micromamba
# ships with, since `_entrypoint.sh` auto-activates `base`. Both envs
# end up package-identical -- only the name differs.

# -- Stage 1: builder ---------------------------------------------------
FROM mambaorg/micromamba:latest AS builder

USER $MAMBA_USER

COPY --chown=$MAMBA_USER:$MAMBA_USER conda-env.yml /tmp/conda-env.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER pyproject.toml README.md LICENSE /app/
COPY --chown=$MAMBA_USER:$MAMBA_USER src /app/src

WORKDIR /app

RUN micromamba install -y -n base -f /tmp/conda-env.yml && \
    micromamba clean --all --yes

# -- Stage 2: runtime ---------------------------------------------------
FROM mambaorg/micromamba:latest

COPY --from=builder /opt/conda /opt/conda
USER $MAMBA_USER
WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER . /app
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Default command: run pytest unit + integration suites. Override via
# `docker run --rm subsideo:dev <cmd>` for ad-hoc introspection.
CMD ["pytest", "tests/unit", "tests/integration", "-q"]
