#!/bin/bash
for iface in eth1 eth2 eth3 eth4; do
  while ! ip link show dev $iface >/dev/null 2>&1; do
    sleep 0.5
  done
done

ip link add name br0 type bridge vlan_filtering 1 || true
ip link set dev br0 up
ip link set dev eth1 master br0 up
ip link set dev eth2 master br0 up
ip link set dev eth3 master br0 up
ip link set dev eth4 master br0 up

# eth1: Trunk to R1 (VLAN 10, 20)
bridge vlan add dev eth1 vid 10 || true
bridge vlan add dev eth1 vid 20 || true
# eth2: Trunk to S2 (VLAN 10, 20, 30)
bridge vlan add dev eth2 vid 10 || true
bridge vlan add dev eth2 vid 20 || true
bridge vlan add dev eth2 vid 30 || true
# eth3: Access port to H1 (VLAN 10)
bridge vlan add dev eth3 vid 10 pvid untagged || true
# eth4: Access port to H2 (VLAN 20)
bridge vlan add dev eth4 vid 20 pvid untagged || true

tail -f /dev/null
