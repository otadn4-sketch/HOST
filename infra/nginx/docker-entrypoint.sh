#!/bin/sh
set -eu
: "${PUBLIC_HOST:=localhost}"
: "${CLIENT_MAX_BODY_SIZE:=64m}"
: "${TLS_CERT_PATH:=/etc/nginx/certs/fullchain.pem}"
: "${TLS_KEY_PATH:=/etc/nginx/certs/privkey.pem}"
envsubst '${PUBLIC_HOST} ${CLIENT_MAX_BODY_SIZE} ${TLS_CERT_PATH} ${TLS_KEY_PATH}' \
  < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
