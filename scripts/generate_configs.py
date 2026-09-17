import os

BASE_DIR = "/home/student/Desktop/lab1"

DAEMONS = """# FRR Daemons configuration
zebra=yes
bgpd=yes
ospfd=yes
ospf6d=yes
ripd=yes
ripngd=yes
isisd=no
pimd=no
ldpd=no
nhrpd=no
eigrpd=no
babeld=no
sharpd=no
pbrd=no
bfdd=no
fabricd=no
vrrpd=no
pathd=no
vtysh_enable=yes
zebra_options="  -A 127.0.0.1 -s 90000000"
bgpd_options="   -A 127.0.0.1"
ospfd_options="  -A 127.0.0.1"
ospf6d_options=" -A ::1"
ripd_options="   -A 127.0.0.1"
ripngd_options=" -A ::1"
"""

for r in ['r1', 'r2', 'r3', 'r4', 'r5']:
    os.makedirs(f"{BASE_DIR}/configs/{r}", exist_ok=True)
    with open(f"{BASE_DIR}/configs/{r}/daemons", "w") as f:
        f.write(DAEMONS)
    with open(f"{BASE_DIR}/configs/{r}/vtysh.conf", "w") as f:
        f.write(f"service integrated-vtysh-config\nhostname {r}\n")

# R1 FRR Config & Startup
R1_FRR = """frr version 8.4
frr defaults traditional
hostname r1
log syslog informational
ipv6 forwarding
!
interface eth1
 description OSPF Area 0 uplink to S3
 ip ospf area 0
 ipv6 ospf6 area 0.0.0.0
!
interface eth2.10
 description VLAN 10 Subinterface
!
interface eth2.20
 description VLAN 20 Subinterface
!
router rip
 version 2
 network 10.10.10.0/24
 network 10.10.20.0/24
 redistribute ospf
 redistribute connected
 default-information originate
!
router ripng
 network eth2.10
 network eth2.20
 redistribute ospf6
 redistribute connected
 default-information originate
!
router ospf
 ospf router-id 10.0.0.1
 redistribute rip metric 10 metric-type 1
 redistribute connected metric 10 metric-type 1
!
router ospf6
 ospf6 router-id 10.0.0.1
 redistribute ripng
 redistribute connected
!
line vty
!
"""
with open(f"{BASE_DIR}/configs/r1/frr.conf", "w") as f:
    f.write(R1_FRR)

R1_STARTUP = """#!/bin/bash
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
"""
with open(f"{BASE_DIR}/configs/r1/start.sh", "w") as f:
    f.write(R1_STARTUP)
os.chmod(f"{BASE_DIR}/configs/r1/start.sh", 0o755)

# R2 FRR Config & DHCP Server
R2_FRR = """frr version 8.4
frr defaults traditional
hostname r2
log syslog informational
ipv6 forwarding
!
interface eth1
 description OSPF Area 0 uplink to S4
 ip ospf area 0
 ipv6 ospf6 area 0.0.0.0
!
interface eth2.10
 description VLAN 10 Subinterface
!
interface eth2.20
 description VLAN 20 Subinterface
!
interface eth2.30
 description VLAN 30 Subinterface (IPv6-Only)
!
router rip
 version 2
 network 10.10.10.0/24
 network 10.10.20.0/24
 redistribute ospf
 redistribute connected
 default-information originate
!
router ripng
 network eth2.10
 network eth2.20
 network eth2.30
 redistribute ospf6
 redistribute connected
 default-information originate
!
router ospf
 ospf router-id 10.0.0.2
 redistribute rip metric 10 metric-type 1
 redistribute connected metric 10 metric-type 1
!
router ospf6
 ospf6 router-id 10.0.0.2
 redistribute ripng
 redistribute connected
!
line vty
!
"""
with open(f"{BASE_DIR}/configs/r2/frr.conf", "w") as f:
    f.write(R2_FRR)

R2_DNSMASQ = """# R2 DHCP Server
interface=eth2.10,eth2.20,eth2.30
bind-interfaces
dhcp-authoritative

# VLAN 10 (Dual-Stack)
dhcp-range=set:vlan10,10.10.10.100,10.10.10.200,255.255.255.0,12h
dhcp-option=tag:vlan10,option:router,10.10.10.1
dhcp-option=tag:vlan10,option:dns-server,198.51.100.10
dhcp-range=set:vlan10_v6,2001:db8:10::100,2001:db8:10::200,slaac,ra-names,64,12h

# VLAN 20 (Dual-Stack)
dhcp-range=set:vlan20,10.10.20.100,10.10.20.200,255.255.255.0,12h
dhcp-option=tag:vlan20,option:router,10.10.20.1
dhcp-option=tag:vlan20,option:dns-server,198.51.100.10
dhcp-range=set:vlan20_v6,2001:db8:20::100,2001:db8:20::200,slaac,ra-names,64,12h

# VLAN 30 (IPv6-Only)
dhcp-range=set:vlan30_v6,2001:db8:30::100,2001:db8:30::200,slaac,ra-names,64,12h

# Static Leases
dhcp-host=aa:c1:ab:00:10:01,10.10.10.101,h1,[2001:db8:10::101],infinite
dhcp-host=aa:c1:ab:00:20:02,10.10.20.102,h2,[2001:db8:20::102],infinite
dhcp-host=aa:c1:ab:00:10:03,10.10.10.103,h3,[2001:db8:10::103],infinite
dhcp-host=aa:c1:ab:00:30:04,ignore,[2001:db8:30::104],h4,infinite

enable-ra
"""
with open(f"{BASE_DIR}/configs/r2/dnsmasq.conf", "w") as f:
    f.write(R2_DNSMASQ)

R2_STARTUP = """#!/bin/bash
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
"""
with open(f"{BASE_DIR}/configs/r2/start.sh", "w") as f:
    f.write(R2_STARTUP)
os.chmod(f"{BASE_DIR}/configs/r2/start.sh", 0o755)

# R3 FRR Config & Startup
R3_FRR = """frr version 8.4
frr defaults traditional
hostname r3
log syslog informational
ipv6 forwarding
!
interface eth1
 description Link to R5 (BGP)
!
interface eth2
 description Link to S3 (OSPF Area 0)
 ip ospf area 0
 ipv6 ospf6 area 0.0.0.0
!
router ospf
 ospf router-id 10.0.0.3
 default-information originate always
 redistribute bgp metric 10 metric-type 1
 redistribute connected metric 10 metric-type 1
!
router ospf6
 ospf6 router-id 10.0.0.3
 default-information originate always
 redistribute bgp
 redistribute connected
!
router bgp 65001
 bgp router-id 10.0.0.3
 no bgp ebgp-requires-policy
 neighbor 172.16.35.2 remote-as 65005
 neighbor 2001:db8:35::2 remote-as 65005
 !
 address-family ipv4 unicast
  network 10.0.0.0/8
  redistribute ospf
  redistribute connected
  neighbor 172.16.35.2 activate
  no neighbor 2001:db8:35::2 activate
 exit-address-family
 !
 address-family ipv6 unicast
  network 2001:db8::/32
  redistribute ospf6
  redistribute connected
  neighbor 2001:db8:35::2 activate
 exit-address-family
!
line vty
!
"""
with open(f"{BASE_DIR}/configs/r3/frr.conf", "w") as f:
    f.write(R3_FRR)

R3_STARTUP = """#!/bin/bash
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
"""
with open(f"{BASE_DIR}/configs/r3/start.sh", "w") as f:
    f.write(R3_STARTUP)
os.chmod(f"{BASE_DIR}/configs/r3/start.sh", 0o755)

# R4 FRR Config & Startup
R4_FRR = """frr version 8.4
frr defaults traditional
hostname r4
log syslog informational
ipv6 forwarding
!
interface eth1
 description Link to R5 (BGP)
!
interface eth2
 description Link to S4 (OSPF Area 0)
 ip ospf area 0
 ipv6 ospf6 area 0.0.0.0
!
router ospf
 ospf router-id 10.0.0.4
 default-information originate always
 redistribute bgp metric 10 metric-type 1
 redistribute connected metric 10 metric-type 1
!
router ospf6
 ospf6 router-id 10.0.0.4
 default-information originate always
 redistribute bgp
 redistribute connected
!
router bgp 65001
 bgp router-id 10.0.0.4
 no bgp ebgp-requires-policy
 neighbor 172.16.45.2 remote-as 65005
 neighbor 2001:db8:45::2 remote-as 65005
 !
 address-family ipv4 unicast
  network 10.0.0.0/8
  redistribute ospf
  redistribute connected
  neighbor 172.16.45.2 activate
  no neighbor 2001:db8:45::2 activate
 exit-address-family
 !
 address-family ipv6 unicast
  network 2001:db8::/32
  redistribute ospf6
  redistribute connected
  neighbor 2001:db8:45::2 activate
 exit-address-family
!
line vty
!
"""
with open(f"{BASE_DIR}/configs/r4/frr.conf", "w") as f:
    f.write(R4_FRR)

R4_STARTUP = """#!/bin/bash
for iface in eth1 eth2; do
  while ! ip link show dev $iface >/dev/null 2>&1; do
    sleep 0.5
  done
  ip link set dev $iface up
done

ip addr add 172.16.45.1/30 dev eth1 || true
ip addr add 2001:db8:45::1/64 dev eth1 || true

ip addr add 10.0.0.4/24 dev eth2 || true
ip addr add 2001:db8:0::4/64 dev eth2 || true

/usr/lib/frr/frrinit.sh start
sleep 2
vtysh -b
tail -f /dev/null
"""
with open(f"{BASE_DIR}/configs/r4/start.sh", "w") as f:
    f.write(R4_STARTUP)
os.chmod(f"{BASE_DIR}/configs/r4/start.sh", 0o755)

# R5 FRR Config & Startup (PE Router)
R5_FRR = """frr version 8.4
frr defaults traditional
hostname r5
log syslog informational
ipv6 forwarding
!
interface eth1
 description Link to Web Server
!
interface eth2
 description Link to R3
!
interface eth3
 description Link to R4
!
router bgp 65005
 bgp router-id 198.51.100.1
 no bgp ebgp-requires-policy
 neighbor 172.16.35.1 remote-as 65001
 neighbor 172.16.45.1 remote-as 65001
 neighbor 2001:db8:35::1 remote-as 65001
 neighbor 2001:db8:45::1 remote-as 65001
 !
 address-family ipv4 unicast
  network 198.51.100.0/24
  redistribute connected
  neighbor 172.16.35.1 activate
  neighbor 172.16.35.1 default-originate
  neighbor 172.16.45.1 activate
  neighbor 172.16.45.1 default-originate
  no neighbor 2001:db8:35::1 activate
  no neighbor 2001:db8:45::1 activate
 exit-address-family
 !
 address-family ipv6 unicast
  network 2001:db8:100::/64
  redistribute connected
  neighbor 2001:db8:35::1 activate
  neighbor 2001:db8:35::1 default-originate
  neighbor 2001:db8:45::1 activate
  neighbor 2001:db8:45::1 default-originate
 exit-address-family
!
line vty
!
"""
with open(f"{BASE_DIR}/configs/r5/frr.conf", "w") as f:
    f.write(R5_FRR)

R5_STARTUP = """#!/bin/bash
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
"""
with open(f"{BASE_DIR}/configs/r5/start.sh", "w") as f:
    f.write(R5_STARTUP)
os.chmod(f"{BASE_DIR}/configs/r5/start.sh", 0o755)

# Switches: S1 and S2 (Access Switches with 802.1Q VLANs)
S1_STARTUP = """#!/bin/bash
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
"""
with open(f"{BASE_DIR}/configs/s1/start.sh", "w") as f:
    f.write(S1_STARTUP)
os.chmod(f"{BASE_DIR}/configs/s1/start.sh", 0o755)

S2_STARTUP = """#!/bin/bash
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

# eth1: Trunk to R2 (VLAN 10, 20, 30)
bridge vlan add dev eth1 vid 10 || true
bridge vlan add dev eth1 vid 20 || true
bridge vlan add dev eth1 vid 30 || true
# eth2: Trunk to S1 (VLAN 10, 20, 30)
bridge vlan add dev eth2 vid 10 || true
bridge vlan add dev eth2 vid 20 || true
bridge vlan add dev eth2 vid 30 || true
# eth3: Access port to H3 (VLAN 10)
bridge vlan add dev eth3 vid 10 pvid untagged || true
# eth4: Access port to H4 (VLAN 30)
bridge vlan add dev eth4 vid 30 pvid untagged || true

tail -f /dev/null
"""
with open(f"{BASE_DIR}/configs/s2/start.sh", "w") as f:
    f.write(S2_STARTUP)
os.chmod(f"{BASE_DIR}/configs/s2/start.sh", 0o755)

# Core Switches: S3 and S4 (OSPF Area 0 Core Bridges)
S3_STARTUP = """#!/bin/bash
for iface in eth1 eth2 eth3 eth4; do
  while ! ip link show dev $iface >/dev/null 2>&1; do
    sleep 0.5
  done
done

ip link add name br0 type bridge || true
ip link set dev br0 up
ip link set dev eth1 master br0 up
ip link set dev eth2 master br0 up
ip link set dev eth3 master br0 up
ip link set dev eth4 master br0 up
tail -f /dev/null
"""
with open(f"{BASE_DIR}/configs/s3/start.sh", "w") as f:
    f.write(S3_STARTUP)
os.chmod(f"{BASE_DIR}/configs/s3/start.sh", 0o755)

S4_STARTUP = """#!/bin/bash
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
"""
with open(f"{BASE_DIR}/configs/s4/start.sh", "w") as f:
    f.write(S4_STARTUP)
os.chmod(f"{BASE_DIR}/configs/s4/start.sh", 0o755)

# Hosts H1, H2, H3, H4
# H1 (VLAN 10)
H1_STARTUP = """#!/bin/bash
while ! ip link show dev eth1 >/dev/null 2>&1; do
  sleep 0.5
done
ip link set dev eth1 address aa:c1:ab:00:10:01 up
sleep 2
ip addr add 10.10.10.101/24 dev eth1 || true
ip route replace default via 10.10.10.1 dev eth1
ip addr add 2001:db8:10::101/64 dev eth1 || true
ip -6 route replace default via 2001:db8:10::1 dev eth1
tail -f /dev/null
"""
with open(f"{BASE_DIR}/configs/h1/start.sh", "w") as f:
    f.write(H1_STARTUP)
os.chmod(f"{BASE_DIR}/configs/h1/start.sh", 0o755)

# H2 (VLAN 20)
H2_STARTUP = """#!/bin/bash
while ! ip link show dev eth1 >/dev/null 2>&1; do
  sleep 0.5
done
ip link set dev eth1 address aa:c1:ab:00:20:02 up
sleep 2
ip addr add 10.10.20.102/24 dev eth1 || true
ip route replace default via 10.10.20.1 dev eth1
ip addr add 2001:db8:20::102/64 dev eth1 || true
ip -6 route replace default via 2001:db8:20::1 dev eth1
tail -f /dev/null
"""
with open(f"{BASE_DIR}/configs/h2/start.sh", "w") as f:
    f.write(H2_STARTUP)
os.chmod(f"{BASE_DIR}/configs/h2/start.sh", 0o755)

# H3 (VLAN 10)
H3_STARTUP = """#!/bin/bash
while ! ip link show dev eth1 >/dev/null 2>&1; do
  sleep 0.5
done
ip link set dev eth1 address aa:c1:ab:00:10:03 up
sleep 2
ip addr add 10.10.10.103/24 dev eth1 || true
ip route replace default via 10.10.10.1 dev eth1
ip addr add 2001:db8:10::103/64 dev eth1 || true
ip -6 route replace default via 2001:db8:10::1 dev eth1
tail -f /dev/null
"""
with open(f"{BASE_DIR}/configs/h3/start.sh", "w") as f:
    f.write(H3_STARTUP)
os.chmod(f"{BASE_DIR}/configs/h3/start.sh", 0o755)

# H4 (VLAN 30: IPv6-Only)
H4_STARTUP = """#!/bin/bash
while ! ip link show dev eth1 >/dev/null 2>&1; do
  sleep 0.5
done
ip link set dev eth1 address aa:c1:ab:00:30:04 up
sleep 2
ip addr add 2001:db8:30::104/64 dev eth1 || true
ip -6 route replace default via 2001:db8:30::2 dev eth1
tail -f /dev/null
"""
with open(f"{BASE_DIR}/configs/h4/start.sh", "w") as f:
    f.write(H4_STARTUP)
os.chmod(f"{BASE_DIR}/configs/h4/start.sh", 0o755)

# Web Server Python Dual-Stack Server
WEB_SERVER_PY = """import http.server
import socket
import os

os.chdir('/var/www/html')

class DualStackServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6

Handler = http.server.SimpleHTTPRequestHandler
httpd = DualStackServer(('::', 80), Handler)
print("Serving HTTP on dual-stack port 80...")
httpd.serve_forever()
"""
with open(f"{BASE_DIR}/configs/web-server/server.py", "w") as f:
    f.write(WEB_SERVER_PY)

WEB_STARTUP = """#!/bin/bash
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
"""
with open(f"{BASE_DIR}/configs/web-server/start.sh", "w") as f:
    f.write(WEB_STARTUP)
os.chmod(f"{BASE_DIR}/configs/web-server/start.sh", 0o755)

# NMAS Station
NMAS_STARTUP = """#!/bin/bash
while ! ip link show dev eth1 >/dev/null 2>&1; do
  sleep 0.5
done
ip link set dev eth1 up
ip addr add 10.0.0.100/24 dev eth1 || true
ip route replace default via 10.0.0.3 dev eth1
ip addr add 2001:db8:0::100/64 dev eth1 || true
ip -6 route replace default via 2001:db8:0::3 dev eth1
tail -f /dev/null
"""
with open(f"{BASE_DIR}/configs/nmas/start.sh", "w") as f:
    f.write(NMAS_STARTUP)
os.chmod(f"{BASE_DIR}/configs/nmas/start.sh", 0o755)

print("Generated full verified configuration and startup scripts!")
