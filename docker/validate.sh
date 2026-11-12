#!/bin/sh
# Rodar dentro do WSL, na raiz do repositório. Gera evidência verdadeira ou falha.
set -eu
mkdir -p evidence/docker
docker compose exec -T edge wg show > evidence/docker/wireguard.txt
docker compose exec -T cloud wg show >> evidence/docker/wireguard.txt
docker compose exec -T edge ip route > evidence/docker/routes.txt
docker compose exec -T edge iptables -S > evidence/docker/firewall-edge.txt
docker compose exec -T cloud iptables -S > evidence/docker/firewall-cloud.txt
docker compose exec -T edge python -c 'import json,urllib.request;from aurora.pki import client_context;r=urllib.request.Request("https://cloud:9443/ingest",data=b"[]",headers={"Content-Type":"application/json"});s=urllib.request.urlopen(r,context=client_context("edge-ubs"));print(s.status)' > evidence/docker/tunnel-https.txt
docker compose exec -T operator python -c 'import socket;s=socket.create_connection(("172.29.20.2",8080),timeout=3);print("PASS: operador alcança painel");s.close()' > evidence/docker/segments.txt
docker compose exec -T operator python -c 'import socket
try:s=socket.create_connection(("172.29.20.2",8883),timeout=3)
except OSError:print("PASS: operador bloqueado no MQTT")
else:s.close();raise SystemExit("FAIL: MQTT acessível ao operador")' >> evidence/docker/segments.txt
docker compose exec -T field python -c 'import socket
try:s=socket.create_connection(("172.29.10.2",8080),timeout=3)
except OSError:print("PASS: IoT bloqueado no painel")
else:s.close();raise SystemExit("FAIL: painel acessível ao IoT")' >> evidence/docker/segments.txt
echo 'Validação básica concluída. Conferir handshake e revisar logs; não prova MFA no túnel.'
