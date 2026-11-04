FROM amforge-send-dev:latest
COPY --chown=coneshare:coneshare backend/ /home/coneshare/app/
COPY --chown=coneshare:coneshare frontend/dist/ /home/coneshare/app/frontend/dist/
COPY brand.yaml /etc/dealroom/brand.yaml
COPY deploy/chief-send-v1/nginx.conf /home/coneshare/runtime/coneshare.nginx.conf
RUN rm -f /home/coneshare/runtime/core-serv.supervisor.conf && find /home/coneshare/runtime/supervisord -type f -exec sed -i '/core-serv/d' {} \;

RUN sed -i 's/strict-origin-when-cross-origin/no-referrer/g' /home/coneshare/runtime/nginx/security-headers.conf
