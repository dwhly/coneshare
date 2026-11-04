# Chief Dealroom layout prototype: send-dev backend + this branch's frontend build.
# Build context = frontend/dist (built natively: see README.md). Only the SPA assets change.
ARG BASE=amforge-send-dev:latest
FROM ${BASE}
RUN rm -rf /home/coneshare/app/frontend/dist
COPY --chown=coneshare:coneshare . /home/coneshare/app/frontend/dist
