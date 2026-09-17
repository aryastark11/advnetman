#!/bin/bash
for iface in eth1 eth2 eth3; do
  while ! ip link show dev $iface >/dev/null 2>&1; do
    sleep 0.5
  done
done

ip link add name br0 type bridge || true
ip link set dev br0 up
ip link set dev eth1 master br0 up
ip link set dev eth2 master br0 up
ip link set dev eth3 master br0 up
tail -f /dev/null
