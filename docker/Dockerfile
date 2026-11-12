FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends wireguard-tools iproute2 iptables mosquitto curl ca-certificates gosu && rm -rf /var/lib/apt/lists/* && useradd --uid 1000 --user-group aurora
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY aurora /app/aurora
COPY docker /app/docker
COPY tests /app/tests
RUN chmod +x /app/docker/*.sh
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENTRYPOINT ["/app/docker/start.sh"]
