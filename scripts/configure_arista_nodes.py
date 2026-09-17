import subprocess
import time

commands = {
    "clab-lab1-r5": """enable
configure
service routing protocols model multi-agent
interface Ethernet1
 no switchport
 ip address 198.51.100.1/24
 ipv6 enable
 ipv6 address 2001:db8:100::1/64
 no shutdown
interface Ethernet2
 no switchport
 ip address 172.16.35.2/30
 ipv6 enable
 ipv6 address 2001:db8:35::2/64
 no shutdown
interface Ethernet3
 no switchport
 ip address 172.16.45.2/30
 ipv6 enable
 ipv6 address 2001:db8:45::2/64
 no shutdown
ip routing
ipv6 unicast-routing
router bgp 65005
 router-id 198.51.100.1
 no shutdown
 neighbor 172.16.35.1 remote-as 65001
 neighbor 172.16.45.1 remote-as 65001
 neighbor 2001:db8:35::1 remote-as 65001
 neighbor 2001:db8:45::1 remote-as 65001
 address-family ipv4
  neighbor 172.16.35.1 activate
  neighbor 172.16.35.1 default-originate
  neighbor 172.16.45.1 activate
  neighbor 172.16.45.1 default-originate
  network 198.51.100.0/24
  redistribute connected
 address-family ipv6
  neighbor 2001:db8:35::1 activate
  neighbor 2001:db8:35::1 default-originate
  neighbor 2001:db8:45::1 activate
  neighbor 2001:db8:45::1 default-originate
  network 2001:db8:100::/64
  redistribute connected
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
""",

    "clab-lab1-r3": """enable
configure
service routing protocols model multi-agent
interface Ethernet1
 no switchport
 ip address 172.16.35.1/30
 ipv6 enable
 ipv6 address 2001:db8:35::1/64
 no shutdown
interface Ethernet2
 no switchport
 ip address 10.0.0.3/24
 ipv6 enable
 ipv6 address 2001:db8::3/64
 ip ospf area 0.0.0.0
 ipv6 ospf 1 area 0.0.0.0
 no shutdown
ip routing
ipv6 unicast-routing
router ospf 1
 router-id 10.0.0.3
 no shutdown
 default-information originate always
 redistribute bgp
 redistribute connected
ipv6 router ospf 1
 router-id 10.0.0.3
 no shutdown
 default-information originate always
 redistribute bgp
 redistribute connected
router bgp 65001
 router-id 10.0.0.3
 no shutdown
 neighbor 172.16.35.2 remote-as 65005
 neighbor 2001:db8:35::2 remote-as 65005
 address-family ipv4
  neighbor 172.16.35.2 activate
  redistribute connected
  redistribute ospf match internal
  redistribute ospf match external
  redistribute ospf match nssa-external
 address-family ipv6
  neighbor 2001:db8:35::2 activate
  redistribute connected
  redistribute ospfv3 match internal
  redistribute ospfv3 match external
  redistribute ospfv3 match nssa-external
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
""",

    "clab-lab1-r4": """enable
configure
service routing protocols model multi-agent
interface Ethernet1
 no switchport
 ip address 172.16.45.1/30
 ipv6 enable
 ipv6 address 2001:db8:45::1/64
 no shutdown
interface Ethernet2
 no switchport
 ip address 10.0.0.4/24
 ipv6 enable
 ipv6 address 2001:db8::4/64
 ip ospf area 0.0.0.0
 ipv6 ospf 1 area 0.0.0.0
 no shutdown
ip routing
ipv6 unicast-routing
router ospf 1
 router-id 10.0.0.4
 no shutdown
 default-information originate always
 redistribute bgp
 redistribute connected
ipv6 router ospf 1
 router-id 10.0.0.4
 no shutdown
 default-information originate always
 redistribute bgp
 redistribute connected
router bgp 65001
 router-id 10.0.0.4
 no shutdown
 neighbor 172.16.45.2 remote-as 65005
 neighbor 2001:db8:45::2 remote-as 65005
 address-family ipv4
  neighbor 172.16.45.2 activate
  redistribute connected
  redistribute ospf match internal
  redistribute ospf match external
  redistribute ospf match nssa-external
 address-family ipv6
  neighbor 2001:db8:45::2 activate
  redistribute connected
  redistribute ospfv3 match internal
  redistribute ospfv3 match external
  redistribute ospfv3 match nssa-external
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
""",

    "clab-lab1-r1": """enable
configure
service routing protocols model multi-agent
interface Ethernet1
 no switchport
 ip address 10.0.0.1/24
 ipv6 enable
 ipv6 address 2001:db8::1/64
 ip ospf area 0.0.0.0
 ipv6 ospf 1 area 0.0.0.0
 no shutdown
interface Ethernet2
 no switchport
 no shutdown
interface Ethernet2.10
 encapsulation dot1q vlan 10
 ip address 10.10.10.1/24
 ipv6 enable
 ipv6 address 2001:db8:10::1/64
 no shutdown
interface Ethernet2.20
 encapsulation dot1q vlan 20
 ip address 10.10.20.1/24
 ipv6 enable
 ipv6 address 2001:db8:20::1/64
 no shutdown
ip routing
ipv6 unicast-routing
router rip
 version 2
 network 10.10.10.0/24
 network 10.10.20.0/24
 redistribute connected
 redistribute ospf
 no shutdown
router ospf 1
 router-id 10.0.0.1
 no shutdown
 redistribute connected
 redistribute rip
ipv6 router ospf 1
 router-id 10.0.0.1
 no shutdown
 redistribute connected
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
""",

    "clab-lab1-r2": """enable
configure
service routing protocols model multi-agent
interface Ethernet1
 no switchport
 ip address 10.0.0.2/24
 ipv6 enable
 ipv6 address 2001:db8::2/64
 ip ospf area 0.0.0.0
 ipv6 ospf 1 area 0.0.0.0
 no shutdown
interface Ethernet2
 no switchport
 no shutdown
interface Ethernet2.10
 encapsulation dot1q vlan 10
 ip address 10.10.10.2/24
 ipv6 enable
 ipv6 address 2001:db8:10::2/64
 dhcp server ipv4
 dhcp server ipv6
 no shutdown
interface Ethernet2.20
 encapsulation dot1q vlan 20
 ip address 10.10.20.2/24
 ipv6 enable
 ipv6 address 2001:db8:20::2/64
 dhcp server ipv4
 dhcp server ipv6
 no shutdown
interface Ethernet2.30
 encapsulation dot1q vlan 30
 ipv6 enable
 ipv6 address 2001:db8:30::2/64
 dhcp server ipv6
 no shutdown
ip routing
ipv6 unicast-routing
router rip
 version 2
 network 10.10.10.0/24
 network 10.10.20.0/24
 redistribute connected
 redistribute ospf
 no shutdown
router ospf 1
 router-id 10.0.0.2
 no shutdown
 redistribute connected
 redistribute rip
ipv6 router ospf 1
 router-id 10.0.0.2
 no shutdown
 redistribute connected
dhcp server
 no disabled
 subnet 10.10.10.0/24
  range 10.10.10.100 10.10.10.200
  default-gateway 10.10.10.1
  dns server 198.51.100.10
 subnet 10.10.20.0/24
  range 10.10.20.100 10.10.20.200
  default-gateway 10.10.20.1
  dns server 198.51.100.10
 subnet 2001:db8:10::/64
  range 2001:db8:10::100 2001:db8:10::200
 subnet 2001:db8:20::/64
  range 2001:db8:20::100 2001:db8:20::200
 subnet 2001:db8:30::/64
  range 2001:db8:30::100 2001:db8:30::200
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
""",

    "clab-lab1-s1": """enable
configure
vlan 10
 name VLAN10
vlan 20
 name VLAN20
vlan 30
 name VLAN30
interface Ethernet1
 description Trunk to R1
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
interface Ethernet2
 description Trunk to S2
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30
 no shutdown
interface Ethernet3
 description Access port H1 (VLAN 10)
 switchport mode access
 switchport access vlan 10
 no shutdown
interface Ethernet4
 description Access port H2 (VLAN 20)
 switchport mode access
 switchport access vlan 20
 no shutdown
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
""",

    "clab-lab1-s2": """enable
configure
vlan 10
 name VLAN10
vlan 20
 name VLAN20
vlan 30
 name VLAN30
interface Ethernet1
 description Trunk to R2
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30
 no shutdown
interface Ethernet2
 description Trunk to S1
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30
 no shutdown
interface Ethernet3
 description Access port H3 (VLAN 10)
 switchport mode access
 switchport access vlan 10
 no shutdown
interface Ethernet4
 description Access port H4 (VLAN 30)
 switchport mode access
 switchport access vlan 30
 no shutdown
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
""",

    "clab-lab1-s3": """enable
configure
vlan 1
 name default
interface Ethernet1
 description Link to R3
 switchport mode access
 no shutdown
interface Ethernet2
 description Link to S4
 switchport mode access
 no shutdown
interface Ethernet3
 description Link to R1
 switchport mode access
 no shutdown
interface Ethernet4
 description Link to NMAS
 switchport mode access
 no shutdown
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
""",

    "clab-lab1-s4": """enable
configure
vlan 1
 name default
interface Ethernet1
 description Link to R4
 switchport mode access
 no shutdown
interface Ethernet2
 description Link to S3
 switchport mode access
 no shutdown
interface Ethernet3
 description Link to R2
 switchport mode access
 no shutdown
snmp-server community public ro
snmp-server community private rw
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public
snmp-server enable traps
logging host 10.0.0.100
logging host 172.20.20.100
logging trap informational
management api http-commands
 protocol http
 no shutdown
management api gnmi
 transport grpc default
  no shutdown
end
write memory
"""
}

if __name__ == '__main__':
    for node, cfg in commands.items():
        print(f'Configuring {node}...')
        res = subprocess.run(['docker', 'exec', node, 'FastCli', '-p', '15', '-c', cfg], capture_output=True, text=True)
        if res.returncode != 0 and 'Copy completed successfully' not in res.stdout:
            print(f'  Warning on {node}: {res.stdout.strip()} {res.stderr.strip()}')
        else:
            print(f'  [OK] {node} configured successfully.')

    print('All Arista nodes configured and saved!')
