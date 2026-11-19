FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    BLENDER_BIN=/usr/bin/blender \
    PYTHON=/usr/bin/python3

RUN apt-get update \
    && apt-get install -y --no-install-recommends blender python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pipeline ./pipeline
COPY workers ./workers

RUN python3 -m venv /opt/forge-venv \
    && /opt/forge-venv/bin/pip install --no-cache-dir jsonschema==4.25.1

ENV PYTHON=/opt/forge-venv/bin/python
CMD ["python3", "workers/generation_worker.py"]
