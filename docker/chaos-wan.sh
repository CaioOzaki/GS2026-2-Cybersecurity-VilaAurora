#!/bin/sh
# Teste Linux real: derruba a interface WireGuard da UBS por 1802 s.
# NÃO EXECUTADO no preparo Windows; gera arquivo somente quando terminar.
set -eu
mkdir -p evidence/docker
docker compose exec -T edge python -c 'from aurora.common import RUNTIME;import sqlite3,json;d=sqlite3.connect(RUNTIME/"ubs.db");print(json.dumps({"local":d.execute("select count(*) from readings").fetchone()[0],"pending":d.execute("select count(*) from outbox").fetchone()[0]}))' > evidence/docker/chaos-before.json
start=$(date +%s)
docker compose exec -T edge ip link set wg0 down
trap 'docker compose exec -T edge ip link set wg0 up' EXIT INT TERM
sleep 1802
end=$(date +%s)
docker compose exec -T edge python -c 'from aurora.common import RUNTIME;import sqlite3,json;d=sqlite3.connect(RUNTIME/"ubs.db");print(json.dumps({"local":d.execute("select count(*) from readings").fetchone()[0],"pending":d.execute("select count(*) from outbox").fetchone()[0]}))' > evidence/docker/chaos-offline.json
docker compose exec -T edge ip link set wg0 up
sleep 30
docker compose exec -T edge python -c 'from aurora.common import RUNTIME;import sqlite3,json;d=sqlite3.connect(RUNTIME/"ubs.db");print(json.dumps({"local":d.execute("select count(*) from readings").fetchone()[0],"pending":d.execute("select count(*) from outbox").fetchone()[0]}))' > evidence/docker/chaos-after.json
printf '{"transport_down_seconds":%s,"scope":"interface WireGuard do piloto UBS"}\n' "$((end-start))" > evidence/docker/chaos-duration.json
trap - EXIT INT TERM
