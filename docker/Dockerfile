FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends wireguard-tools iproute2 iptables mosquitto curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY aurora /app/aurora
COPY docker /app/docker
RUN chmod +x /app/docker/*.sh
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["/app/docker/start.sh"]
