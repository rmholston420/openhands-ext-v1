# syntax=docker/dockerfile:1.7
#
# Overlay agent-server image applying ADR-0034 client-side SDK patch inside the
# DockerWorkspace container. Per ADR-0035 — required because RemoteConversation
# crosses the client/container boundary and both endpoints must run the patched
# SDK for `LLM`'s `DiscriminatedUnionMixin` dispatch to survive.
#
# Build context is the repo root. `vendor/openhands-sdk/openhands-sdk/` is
# category-2 regenerable per ADR-0003; scripts/build-patched-agent-server-image.sh
# ensures the vendor tree is fresh before docker build.

ARG BASE_IMAGE=ghcr.io/openhands/agent-server:latest-python
FROM ${BASE_IMAGE}

USER root

# Overlay patched openhands-sdk on top of the pre-built /agent-server/.venv.
# Base image is built with `uv sync --no-editable --managed-python`; the
# resulting venv is pip-less by design, so we use `uv pip install --python`
# (uv is present at /bin/uv per the upstream Dockerfile) to overlay the
# patched package. --no-deps because the base image's uv sync already
# resolved the graph; we only replace the openhands-sdk source. --reinstall
# forces a fresh install even though the version string is unchanged.
COPY --chown=openhands:openhands vendor/openhands-sdk/openhands-sdk /agent-server/openhands-sdk-patched

RUN /bin/uv pip install \
      --python /agent-server/.venv/bin/python \
      --no-deps \
      --reinstall \
      /agent-server/openhands-sdk-patched \
 && /agent-server/.venv/bin/python -c "\
from openhands.sdk.utils.models import DiscriminatedUnionMixin;\
from openhands.sdk.llm.llm import LLM;\
assert DiscriminatedUnionMixin in LLM.__mro__, 'ADR-0034 patch missing in container SDK';\
print('ADR-0034 patch verified in container:', [c.__name__ for c in LLM.__mro__])\
"

USER openhands
