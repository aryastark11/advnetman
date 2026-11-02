#!/bin/bash
while ! ip link show dev eth1 >/dev/null 2>&1; do
  sleep 0.5
done
ip link set dev eth1 address aa:c1:ab:00:10:07 up
sleep 1
ip addr add 10.80.10.107/24 dev eth1 || true
ip route replace default via 10.80.10.1 dev eth1
ip -6 addr add 2001:db8:80:10::107/64 dev eth1 || true
ip -6 route replace default via 2001:db8:80:10::1 dev eth1 || true
echo "nameserver 198.51.100.10" > /etc/resolv.conf || true
tail -f /dev/null
