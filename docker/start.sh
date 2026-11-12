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
  if [ "${ROLE}" = cloud ]; then PEER=172.29.0.3; else PEER=172.29.0.2; fi
  iptables -A INPUT -s "${PEER}/32" -p udp --dport 51820 -j ACCEPT
  chown -R aurora:aurora /state
  chmod 700 /state/pki
  chmod 600 /state/pki/*.key /state/wg0.conf
fi
case "${ROLE}" in
 cloud)
  iptables -A INPUT -i wg0 -s 10.77.0.2/32 -p tcp --dport 9443 -j ACCEPT
  exec gosu aurora python -m aurora.cloud
  ;;
 edge)
  iptables -A INPUT -s 172.29.10.0/24 -p tcp --dport 8883 -j ACCEPT
  iptables -A INPUT -s 172.29.20.0/24 -p tcp --dport 8080 -j ACCEPT
  iptables -A INPUT -s 172.29.30.0/24 -p tcp --dport 8080 -j ACCEPT
  iptables -A OUTPUT -d 172.29.0.2/32 -p tcp --dport 9443 -j REJECT
  mosquitto -c /state/mosquitto.conf &
  exec gosu aurora python -m aurora.container_edge
  ;;
 field)
  chown -R aurora:aurora /state
  chmod 700 /state/pki
  chmod 600 /state/pki/*.key
  exec gosu aurora python -m aurora.container_field
  ;;
 viewer)
  iptables -P INPUT DROP
  iptables -P FORWARD DROP
  iptables -P OUTPUT DROP
  iptables -A INPUT -i lo -j ACCEPT
  iptables -A OUTPUT -o lo -j ACCEPT
  iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A INPUT -p tcp --dport 8088 -j ACCEPT
  iptables -A OUTPUT -d 172.29.20.2/32 -p tcp --dport 8080 -j ACCEPT
  exec gosu aurora python -m aurora.viewer
  ;;
 observer) exec gosu aurora sleep infinity ;;
 *) exit 2 ;;
esac
