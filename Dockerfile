ARG BRANCH=main
ARG REPO=ghcr.io/midwestfurryfandom/rams
FROM ${REPO}:${BRANCH}
ENV uber_plugins=["mff_rams_plugin"]

# install plugins
COPY . plugins/mff_rams_plugin/

RUN $HOME/.local/bin/uv pip install --system -r plugins/mff/requirements.txt
