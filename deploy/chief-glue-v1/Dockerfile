# Reuse installed native dependencies, then copy this branch's complete backend.
FROM chief-send-proto:latest
COPY --chown=coneshare:coneshare backend/ /home/coneshare/app/
COPY --chown=coneshare:coneshare brand.yaml /home/coneshare/brand.yaml
COPY deploy/chief-glue-v1/nginx.conf /home/coneshare/runtime/coneshare.nginx.conf
RUN pip install --no-cache-dir PyYAML==6.0.3 && mkdir -p /data && chown coneshare:coneshare /data
