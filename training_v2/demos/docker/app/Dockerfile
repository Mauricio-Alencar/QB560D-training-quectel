ARG BASE_IMAGE=python:3.11-slim-bookworm
FROM ${BASE_IMAGE}
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_VERSION=1.0.0
COPY telemetry.py /app/telemetry.py
LABEL com.quectel.training.demo="qb560d-docker" org.opencontainers.image.version="1.0.0"
USER 65534:65534
EXPOSE 8081
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/health', timeout=2).read()"]
CMD ["python3", "/app/telemetry.py", "--host", "0.0.0.0", "--port", "8081"]
