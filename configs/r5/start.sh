#!/bin/bash
for iface in eth1 eth2 eth3; do
  while ! ip link show dev $iface >/dev/null 2>&1; do
    sleep 0.5
  done
  ip link set dev $iface up
done

ip addr add 198.51.100.1/24 dev eth1 || true
ip addr add 2001:db8:100::1/64 dev eth1 || true

ip addr add 172.16.35.2/30 dev eth2 || true
ip addr add 2001:db8:35::2/64 dev eth2 || true

ip addr add 172.16.45.2/30 dev eth3 || true
ip addr add 2001:db8:45::2/64 dev eth3 || true

/usr/lib/frr/frrinit.sh start
sleep 2
vtysh -b
tail -f /dev/null
