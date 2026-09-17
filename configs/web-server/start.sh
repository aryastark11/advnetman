#!/bin/bash
while ! ip link show dev eth1 >/dev/null 2>&1; do
  sleep 0.5
done
ip link set dev eth1 up
ip addr add 198.51.100.10/24 dev eth1 || true
ip route replace default via 198.51.100.1 dev eth1
ip addr add 2001:db8:100::10/64 dev eth1 || true
ip -6 route replace default via 2001:db8:100::1 dev eth1
python3 /server.py &
tail -f /dev/null
