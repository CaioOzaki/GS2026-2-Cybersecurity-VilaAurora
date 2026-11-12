#!/bin/sh
set -eu
if [ "${ROLE}" = cloud ] || [ "${ROLE}" = edge ]; then
  umask 077
  cp /state/wg0.conf /tmp/wg0.conf
  wg-quick up /tmp/wg0.conf
  iptables -P INPUT DROP
  iptables -P FORWARD DROP
  iptables -A INPUT -i lo -j ACCEPT
  iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A INPUT -p udp --dport 51820 -j ACCEPT
fi
case "${ROLE}" in
 cloud)
  iptables -A INPUT -i wg0 -s 10.77.0.2/32 -p tcp --dport 9443 -j ACCEPT
  exec python -m aurora.cloud
  ;;
 edge)
  iptables -A INPUT -s 172.29.10.0/24 -p tcp --dport 8883 -j ACCEPT
  iptables -A INPUT -s 172.29.20.0/24 -p tcp --dport 8080 -j ACCEPT
  iptables -A INPUT -s 172.29.30.0/24 -p tcp --dport 8080 -j ACCEPT
  iptables -A OUTPUT -d 172.29.0.2/32 -p tcp --dport 9443 -j REJECT
  mosquitto -c /state/mosquitto.conf &
  exec python -m aurora.container_edge
  ;;
 field) exec python -m aurora.container_field ;;
 observer) exec sleep infinity ;;
 *) exit 2 ;;
esac
