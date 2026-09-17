#!/bin/bash
for iface in eth1 eth2; do
  while ! ip link show dev $iface >/dev/null 2>&1; do
    sleep 0.5
  done
  ip link set dev $iface up
done

ip addr add 10.0.0.2/24 dev eth1 || true
ip addr add 2001:db8:0::2/64 dev eth1 || true

ip link add link eth2 name eth2.10 type vlan id 10 || true
ip link set dev eth2.10 up
ip addr add 10.10.10.2/24 dev eth2.10 || true
ip addr add 2001:db8:10::2/64 dev eth2.10 || true

ip link add link eth2 name eth2.20 type vlan id 20 || true
ip link set dev eth2.20 up
ip addr add 10.10.20.2/24 dev eth2.20 || true
ip addr add 2001:db8:20::2/64 dev eth2.20 || true

ip link add link eth2 name eth2.30 type vlan id 30 || true
ip link set dev eth2.30 up
ip addr add 2001:db8:30::2/64 dev eth2.30 || true

/usr/lib/frr/frrinit.sh start
sleep 2
vtysh -b
dnsmasq -C /etc/dnsmasq.conf
tail -f /dev/null
