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
# --no-deps: dependency graph is already resolved by the base image's uv sync;
#            we only replace the package source.
# --force-reinstall: base image installs from the same version string, so pip
#                    would otherwise no-op.
COPY --chown=openhands:openhands vendor/openhands-sdk/openhands-sdk /agent-server/openhands-sdk-patched

RUN /agent-server/.venv/bin/pip install \
      --no-deps \
      --force-reinstall \
      --disable-pip-version-check \
      /agent-server/openhands-sdk-patched \
 && /agent-server/.venv/bin/python -c "\
from openhands.sdk.utils.models import DiscriminatedUnionMixin;\
from openhands.sdk.llm.llm import LLM;\
assert DiscriminatedUnionMixin in LLM.__mro__, 'ADR-0034 patch missing in container SDK';\
print('ADR-0034 patch verified in container:', [c.__name__ for c in LLM.__mro__])\
"

USER openhands
