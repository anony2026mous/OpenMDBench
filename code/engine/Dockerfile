FROM python:3.11.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/openmdbench-matplotlib

WORKDIR /app
RUN groupadd --system --gid 10001 openmdbench \
    && useradd --system --uid 10001 --gid openmdbench --home-dir /app openmdbench

COPY pyproject.toml README.md ./
COPY openmdbench ./openmdbench
RUN python -m pip install --no-cache-dir ".[core,server]" \
    && mkdir -p /app/var/audit /app/var/replays /tmp/openmdbench-matplotlib \
    && chown -R openmdbench:openmdbench /app/var /tmp/openmdbench-matplotlib

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2).read()"
CMD ["python", "-m", "uvicorn", "openmdbench.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
