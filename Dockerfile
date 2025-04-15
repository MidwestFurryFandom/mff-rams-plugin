ARG BRANCH=main
ARG REPO=ghcr.io/midwestfurryfandom/rams
FROM ${REPO}:${BRANCH}
ENV uber_plugins=["mff"]

# install plugins
COPY . plugins/mff/

RUN $HOME/.local/bin/uv pip install --system -r plugins/mff/requirements.txt
RUN ln -s mff_rams_plugin plugins/mff/mff