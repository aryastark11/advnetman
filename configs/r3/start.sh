#!/bin/bash
for iface in eth1 eth2; do
  while ! ip link show dev $iface >/dev/null 2>&1; do
    sleep 0.5
  done
  ip link set dev $iface up
done

ip addr add 172.16.35.1/30 dev eth1 || true
ip addr add 2001:db8:35::1/64 dev eth1 || true

ip addr add 10.0.0.3/24 dev eth2 || true
ip addr add 2001:db8:0::3/64 dev eth2 || true

/usr/lib/frr/frrinit.sh start
sleep 2
vtysh -b
tail -f /dev/null
