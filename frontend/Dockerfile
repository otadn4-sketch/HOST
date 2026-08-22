FROM node:22-bookworm-slim AS build
WORKDIR /src
COPY frontend/package.json /src/
RUN npm install
COPY frontend /src
RUN npm run build

FROM nginx:1.27-alpine
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /src/dist /usr/share/nginx/html
COPY infra/nginx/frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
