FROM node:22-bookworm-slim AS build
WORKDIR /src
COPY frontend/package.json /src/
RUN npm install
COPY frontend /src
RUN npm run build

FROM nginx:1.27-alpine
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /src/dist /opt/eytan/frontend-image
COPY VERSION /opt/eytan/frontend-image/VERSION
COPY infra/nginx/frontend.conf /etc/nginx/conf.d/default.conf
COPY infra/frontend-sync.sh /docker-entrypoint.d/99-eytan-sync-live.sh
RUN chmod +x /docker-entrypoint.d/99-eytan-sync-live.sh \
    && cp -a /opt/eytan/frontend-image/. /usr/share/nginx/html/ \
    && chown -R 10001:10001 /usr/share/nginx/html /opt/eytan/frontend-image \
    && chmod -R a+rX /usr/share/nginx/html /opt/eytan/frontend-image
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
