FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gosu ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -u 1000 -m -s /bin/bash agent
WORKDIR /app

# RUNTIME_VERSION is forwarded from molecule-ci's reusable publish
# workflow as a docker build-arg. Cascade-triggered builds set it to
# the exact runtime version PyPI just published. Including it as an
# ARG changes the cache key for the pip install layer below — the
# fix for the cascade cache trap that bit us 5x on 2026-04-27.
ARG RUNTIME_VERSION=
ARG PIP_INDEX_URL=https://git.moleculesai.app/api/packages/molecule-ai/pypi/simple/
ARG PIP_EXTRA_INDEX_URL=https://pypi.org/simple/

# Bump pip + setuptools + wheel BEFORE installing project deps —
# the python:3.11-slim base ships old transitives (jaraco.context 5.3.0,
# wheel 0.45.1, setuptools 65.x) that Trivy flags as fixable HIGH CVEs.
# Bumping here resolves them at the metadata layer; subsequent pip
# installs use the upgraded resolvers. molecule-ci#38 Phase-1.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" --extra-index-url "${PIP_EXTRA_INDEX_URL}" -r requirements.txt && \
    if [ -n "${RUNTIME_VERSION}" ]; then \
      pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" --extra-index-url "${PIP_EXTRA_INDEX_URL}" --upgrade "molecule-ai-workspace-runtime==${RUNTIME_VERSION}"; \
    fi

COPY adapter.py .
COPY __init__.py .

ENV ADAPTER_MODULE=adapter

# Drop-priv entrypoint — per-template privilege contract
# (RFC internal#456). Without this, molecule-runtime ran as ROOT and the
# untrusted agent workload had root capabilities in-container. The
# entrypoint runs as root only long enough to chown /configs to
# agent:agent (so /configs/.auth_token stays agent-readable when the
# runtime writes it in SaaS mode) then re-execs the runtime via
# `gosu agent` so the final process is uid-1000. Both halves are atomic
# — dropping privilege without the chown would regress list_peers to
# the Hermes 401 class.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
