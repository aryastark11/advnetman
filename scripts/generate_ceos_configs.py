import os

BASE_DIR = "/home/student/Desktop/lab1/configs/ceos"
os.makedirs(BASE_DIR, exist_ok=True)

R1_CFG = """! Command: show running-config at line 1
! device: r1 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$0EpeAr86ZqgoZ07r$xiDp3lefZnL6ZYJ3h1ZfuVyLAbj6C.i9G5nCgmI62QuGlXqSjPPJSur6O77/CkgMHP/p7P1RqKBGk8neu4SMO.
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname r1
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
interface Ethernet1
   no switchport
   ip address 10.0.0.1/24
   ipv6 enable
   ipv6 address 2001:db8::1/64
   ip ospf area 0.0.0.0
   ipv6 ospf 1 area 0.0.0.0
!
interface Ethernet2
   no switchport
!
interface Ethernet2.10
   encapsulation dot1q vlan 10
   ip address 10.10.10.1/24
   ipv6 enable
   ipv6 address 2001:db8:10::1/64
!
interface Ethernet2.20
   encapsulation dot1q vlan 20
   ip address 10.10.20.1/24
   ipv6 enable
   ipv6 address 2001:db8:20::1/64
!
interface Management0
   ipv6 address 2001:db8:ffff::9/64
!
interface Management1
   ip address 172.20.20.11/24
   ipv6 address 2001:db8:ffff::5/64
!
ip routing
!
ipv6 unicast-routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
router ospf 1
   router-id 10.0.0.1
   redistribute connected
   redistribute rip
   max-lsa 12000
!
ipv6 router ospf 1
   router-id 10.0.0.1
   redistribute connected
!
router rip
   network 10.10.10.0/24
   network 10.10.20.0/24
   redistribute ospf
   no shutdown
!
end
"""

R2_CFG = """! Command: show running-config at line 1
! device: r2 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$NcD1My7fPiIqFlsi$udfWJ/96RzXzE6j4ucpOv21wYBpnlzo6GvWiFBqipCwO7ExZVp1scApXjdvY63FvNBO2EQ573SFNpipDamax/1
!
dhcp server
   subnet 10.10.10.0/24
      range 10.10.10.100 10.10.10.200
      dns server 198.51.100.10
      default-gateway 10.10.10.1
   !
   subnet 10.10.20.0/24
      range 10.10.20.100 10.10.20.200
      dns server 198.51.100.10
      default-gateway 10.10.20.1
   !
   subnet 2001:db8:10::/64
      range 2001:db8:10::100 2001:db8:10::200
   !
   subnet 2001:db8:20::/64
      range 2001:db8:20::100 2001:db8:20::200
   !
   subnet 2001:db8:30::/64
      range 2001:db8:30::100 2001:db8:30::200
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname r2
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
interface Ethernet1
   no switchport
   ip address 10.0.0.2/24
   ipv6 enable
   ipv6 address 2001:db8::2/64
   ip ospf area 0.0.0.0
   ipv6 ospf 1 area 0.0.0.0
!
interface Ethernet2
   no switchport
!
interface Ethernet2.10
   encapsulation dot1q vlan 10
   ip address 10.10.10.2/24
   dhcp server ipv4
   dhcp server ipv6
   ipv6 enable
   ipv6 address 2001:db8:10::2/64
!
interface Ethernet2.20
   encapsulation dot1q vlan 20
   ip address 10.10.20.2/24
   dhcp server ipv4
   dhcp server ipv6
   ipv6 enable
   ipv6 address 2001:db8:20::2/64
!
interface Ethernet2.30
   encapsulation dot1q vlan 30
   dhcp server ipv6
   ipv6 enable
   ipv6 address 2001:db8:30::2/64
!
interface Management0
   ipv6 address 2001:db8:ffff::7/64
!
interface Management1
   ip address 172.20.20.12/24
   ipv6 address 2001:db8:ffff::4/64
!
ip routing
!
ipv6 unicast-routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
router ospf 1
   router-id 10.0.0.2
   redistribute connected
   redistribute rip
   max-lsa 12000
!
ipv6 router ospf 1
   router-id 10.0.0.2
   redistribute connected
!
router rip
   network 10.10.10.0/24
   network 10.10.20.0/24
   redistribute ospf
   no shutdown
!
end
"""

R3_CFG = """! Command: show running-config at line 1
! device: r3 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$jF9WaU./THpbYlMP$GDdLOuLqfND5Z7q4gfIBfXIR5mucIteYDCkMNpCGTDPUiBwfY.udz5A/ZO9WjbN9SEurJI1M4mJ4LokecC36c1
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname r3
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
interface Ethernet1
   no switchport
   ip address 172.16.35.1/30
   ipv6 enable
   ipv6 address 2001:db8:35::1/64
!
interface Ethernet2
   no switchport
   ip address 10.0.0.3/24
   ipv6 enable
   ipv6 address 2001:db8::3/64
   ip ospf area 0.0.0.0
   ipv6 ospf 1 area 0.0.0.0
!
interface Management0
   ipv6 address 2001:db8:ffff::c/64
!
interface Management1
   ip address 172.20.20.13/24
   ipv6 address 2001:db8:ffff::a/64
!
ip routing
!
ipv6 unicast-routing
!
router bgp 65001
   router-id 10.0.0.3
   neighbor 172.16.35.2 remote-as 65005
   neighbor 2001:db8:35::2 remote-as 65005
   !
   address-family ipv4
      neighbor 172.16.35.2 activate
      network 10.0.0.0/8
      redistribute connected
      redistribute ospf match internal
      redistribute ospf match external
      redistribute ospf match nssa-external
   !
   address-family ipv6
      neighbor 2001:db8:35::2 activate
      network 2001:db8::/32
      redistribute connected
      redistribute ospfv3 match internal
      redistribute ospfv3 match external
      redistribute ospfv3 match nssa-external
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
router ospf 1
   router-id 10.0.0.3
   redistribute bgp
   redistribute connected
   max-lsa 12000
   default-information originate always
!
ipv6 router ospf 1
   router-id 10.0.0.3
   redistribute bgp
   redistribute connected
   default-information originate always
!
end
"""

R4_CFG = """! Command: show running-config at line 1
! device: r4 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$tjO.EU5QNfcXmYvl$D8MPu5ruP40ehU5wqsjcICFXcccTT5uZcJg7UFV4g193COWKmRbUYg9aP7P58NBwbI2LfLV2xeV1p4nXvyj95.
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname r4
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
interface Ethernet1
   no switchport
   ip address 172.16.45.1/30
   ipv6 enable
   ipv6 address 2001:db8:45::1/64
!
interface Ethernet2
   no switchport
   ip address 10.0.0.4/24
   ipv6 enable
   ipv6 address 2001:db8::4/64
   ip ospf area 0.0.0.0
   ipv6 ospf 1 area 0.0.0.0
!
interface Management0
   ipv6 address 2001:db8:ffff::8/64
!
interface Management1
   ip address 172.20.20.14/24
   ipv6 address 2001:db8:ffff::9/64
!
ip routing
!
ipv6 unicast-routing
!
router bgp 65001
   router-id 10.0.0.4
   neighbor 172.16.45.2 remote-as 65005
   neighbor 2001:db8:45::2 remote-as 65005
   !
   address-family ipv4
      neighbor 172.16.45.2 activate
      network 10.0.0.0/8
      redistribute connected
      redistribute ospf match internal
      redistribute ospf match external
      redistribute ospf match nssa-external
   !
   address-family ipv6
      neighbor 2001:db8:45::2 activate
      network 2001:db8::/32
      redistribute connected
      redistribute ospfv3 match internal
      redistribute ospfv3 match external
      redistribute ospfv3 match nssa-external
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
router ospf 1
   router-id 10.0.0.4
   redistribute bgp
   redistribute connected
   max-lsa 12000
   default-information originate always
!
ipv6 router ospf 1
   router-id 10.0.0.4
   redistribute bgp
   redistribute connected
   default-information originate always
!
end
"""

R5_CFG = """! Command: show running-config at line 1
! device: r5 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$m2wcxO0dPfHBmcpZ$LUcxn7jXyPDk6Ze8FESKKOAma1fiH6EiCuw4RnbFWe/Mg.rxebhx9nAtQev7opVMIpyB2wH9Qffq9XHKSP0PD1
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname r5
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
interface Ethernet1
   no switchport
   ip address 198.51.100.1/24
   ipv6 enable
   ipv6 address 2001:db8:100::1/64
!
interface Ethernet2
   no switchport
   ip address 172.16.35.2/30
   ipv6 enable
   ipv6 address 2001:db8:35::2/64
!
interface Ethernet3
   no switchport
   ip address 172.16.45.2/30
   ipv6 enable
   ipv6 address 2001:db8:45::2/64
!
interface Management0
!
interface Management1
   ip address 172.20.20.15/24
   ipv6 address 2001:db8:ffff::e/64
!
ip routing
!
ipv6 unicast-routing
!
router bgp 65005
   router-id 198.51.100.1
   neighbor 172.16.35.1 remote-as 65001
   neighbor 172.16.45.1 remote-as 65001
   neighbor 2001:db8:35::1 remote-as 65001
   neighbor 2001:db8:45::1 remote-as 65001
   !
   address-family ipv4
      neighbor 172.16.35.1 activate
      neighbor 172.16.35.1 default-originate
      neighbor 172.16.45.1 activate
      neighbor 172.16.45.1 default-originate
      network 198.51.100.0/24
      redistribute connected
   !
   address-family ipv6
      neighbor 2001:db8:35::1 activate
      neighbor 2001:db8:35::1 default-originate
      neighbor 2001:db8:45::1 activate
      neighbor 2001:db8:45::1 default-originate
      network 2001:db8:100::/64
      redistribute connected
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
end
"""

S1_CFG = """! Command: show running-config at line 1
! device: s1 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$DsBMK/MANkiZ0KR.$V2DWNZU0O6WAf5pA9sTXtucl77FbyCdTcrKnuMhPBWlCwmX18WbY0nBhFTn4hZi8VpTv.KRk77WTN3NqR2VzU/
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname s1
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
vlan 10
   name VLAN10
!
vlan 20
   name VLAN20
!
vlan 30
   name VLAN30
!
interface Ethernet1
   description Trunk to R1
   switchport trunk allowed vlan 10,20
   switchport mode trunk
!
interface Ethernet2
   description Trunk to S2
   switchport trunk allowed vlan 10,20,30
   switchport mode trunk
!
interface Ethernet3
   description Access port H1 (VLAN 10)
   switchport access vlan 10
!
interface Ethernet4
   description Access port H2 (VLAN 20)
   switchport access vlan 20
!
interface Management0
   ipv6 address 2001:db8:ffff::4/64
!
interface Management1
   ip address 172.20.20.21/24
   ipv6 address 2001:db8:ffff::7/64
!
no ip routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
end
"""

S2_CFG = """! Command: show running-config at line 1
! device: s2 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$ai5AFiXTnY6yrJ7U$coa5//fpYcU5uaGhAGIiVEygaNn/vjY0Uh2d9K4LF9w5UGofJpNkbMbHFZtYfqPJKGL4yAaRlY9f6OS6q21jl.
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname s2
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
vlan 10
   name VLAN10
!
vlan 20
   name VLAN20
!
vlan 30
   name VLAN30
!
interface Ethernet1
   description Trunk to R2
   switchport trunk allowed vlan 10,20,30
   switchport mode trunk
!
interface Ethernet2
   description Trunk to S1
   switchport trunk allowed vlan 10,20,30
   switchport mode trunk
!
interface Ethernet3
   description Access port H3 (VLAN 10)
   switchport access vlan 10
!
interface Ethernet4
   description Access port H4 (VLAN 30)
   switchport access vlan 30
!
interface Management0
   ipv6 address 2001:db8:ffff::5/64
!
interface Management1
   ip address 172.20.20.22/24
   ipv6 address 2001:db8:ffff::6/64
!
no ip routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
end
"""

S3_CFG = """! Command: show running-config at line 1
! device: s3 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$CXEfjZB6r1hJTpgQ$ys7lfpM0Cz.knyilVCc6AUcE58EeAFLnOGx7EQO8kEsgAvBRVQF/ZeQAE7cjmogGDQluy0opY.fTp7tCY2YM/0
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname s3
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
interface Ethernet1
   description Link to R3
!
interface Ethernet2
   description Link to S4
!
interface Ethernet3
   description Link to R1
!
interface Ethernet4
   description Link to NMAS
!
interface Management0
!
interface Management1
   ip address 172.20.20.23/24
   ipv6 address 2001:db8:ffff::f/64
!
no ip routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
end
"""

S4_CFG = """! Command: show running-config at line 1
! device: s4 (cEOSLab, EOS-4.33.10M-49734529.43310M (engineering build))
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$CA9QQrUm/OgGG7Kh$7dgwUNYacct7Hqri4Y4yzeuk1Uv1C.N9JcHpuIXF5rwFeiYf9zpoNS/7o3wqzS/LZcXc5NQ0/dNocEpMuH5BQ0
!
no service interface inactive port-id allocation disabled
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname s4
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
interface Ethernet1
   description Link to R4
!
interface Ethernet2
   description Link to S3
!
interface Ethernet3
   description Link to R2
!
interface Management0
   ipv6 address 2001:db8:ffff::6/64
!
interface Management1
   ip address 172.20.20.24/24
   ipv6 address 2001:db8:ffff::3/64
!
no ip routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
end
"""

configs = {
    "r1.cfg": R1_CFG,
    "r2.cfg": R2_CFG,
    "r3.cfg": R3_CFG,
    "r4.cfg": R4_CFG,
    "r5.cfg": R5_CFG,
    "s1.cfg": S1_CFG,
    "s2.cfg": S2_CFG,
    "s3.cfg": S3_CFG,
    "s4.cfg": S4_CFG,
}

for filename, content in configs.items():
    with open(os.path.join(BASE_DIR, filename), "w") as f:
        f.write(content)

print("All Arista cEOS configurations written to configs/ceos/!")
