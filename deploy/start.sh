#!/bin/sh
set -eu

: "${PORT:=10000}"
: "${BACKEND_PORT:=8000}"
: "${FRONTEND_PORT:=3000}"

export PORT BACKEND_PORT FRONTEND_PORT

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL must be configured before starting BuildSync" >&2
  exit 1
fi

if [ "${SEED_DEMO_USERS:-false}" = "true" ]; then
  PYTHONPATH=/app/backend python3 /app/backend/scripts/seed_demo_users.py
fi
envsubst '${PORT} ${BACKEND_PORT} ${FRONTEND_PORT}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/buildsync.conf
