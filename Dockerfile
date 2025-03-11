ARG BRANCH=main
ARG REPO=gitlab.furfest.org:5050/rams/rams
FROM ${REPO}:${BRANCH}
ENV uber_plugins=["mff"]

# install plugins
COPY . plugins/mff/

RUN /root/.local/bin/uv pip install --system -r plugins/mff/requirements.txt
RUN ln -s mff_rams_plugin plugins/mff/mff