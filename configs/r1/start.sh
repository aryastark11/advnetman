#!/bin/bash
for iface in eth1 eth2; do
  while ! ip link show dev $iface >/dev/null 2>&1; do
    sleep 0.5
  done
  ip link set dev $iface up
done

ip addr add 10.0.0.1/24 dev eth1 || true
ip addr add 2001:db8:0::1/64 dev eth1 || true

ip link add link eth2 name eth2.10 type vlan id 10 || true
ip link set dev eth2.10 up
ip addr add 10.10.10.1/24 dev eth2.10 || true
ip addr add 2001:db8:10::1/64 dev eth2.10 || true

ip link add link eth2 name eth2.20 type vlan id 20 || true
ip link set dev eth2.20 up
ip addr add 10.10.20.1/24 dev eth2.20 || true
ip addr add 2001:db8:20::1/64 dev eth2.20 || true

/usr/lib/frr/frrinit.sh start
sleep 2
vtysh -b
tail -f /dev/null
