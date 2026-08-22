FROM python:3.12-slim-bookworm
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin eytan-upd
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend/app /app/app
COPY update-agent/agent.py /app/agent.py
USER 10001:10001
EXPOSE 8787
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health')"
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8787"]
