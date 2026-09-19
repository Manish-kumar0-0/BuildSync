FROM node:22-bookworm AS frontend-build

WORKDIR /app/site-intel-pro
COPY site-intel-pro/package*.json ./
RUN npm ci
COPY site-intel-pro/ ./
ENV VITE_API_BASE_URL=
RUN npm run build

FROM node:22-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_PORT=3000 \
    BACKEND_PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip nginx supervisor gettext-base \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /app/backend/requirements.txt
COPY backend /app/backend
COPY --from=frontend-build /app/site-intel-pro/.output /app/site-intel-pro/.output
COPY deploy/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY deploy/supervisord.conf /etc/supervisor/conf.d/buildsync.conf
COPY deploy/start.sh /app/deploy/start.sh
RUN chmod +x /app/deploy/start.sh

EXPOSE 10000
CMD ["/app/deploy/start.sh"]
