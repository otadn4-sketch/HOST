FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin eytan

WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /opt/eytan/image/app
COPY backend/alembic /opt/eytan/image/alembic
COPY backend/alembic.ini /opt/eytan/image/alembic.ini
COPY VERSION /opt/eytan/image/VERSION
COPY backend/docker-entrypoint.py /usr/local/bin/eytan-backend-entry.py
RUN cp -a /opt/eytan/image/. /app/ \
    && chown -R eytan:eytan /opt/eytan /app /usr/local/bin/eytan-backend-entry.py \
    && mkdir -p /var/lib/eytan/vault /var/lib/eytan/quarantine /var/lib/eytan/backups \
      /var/lib/eytan/releases /var/lib/eytan/staging \
    && chown -R eytan:eytan /var/lib/eytan

USER eytan
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
ENTRYPOINT ["python3", "/usr/local/bin/eytan-backend-entry.py"]
