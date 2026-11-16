# Runbook: VARP Gateway Down / Virtual Router Failure

## Symptoms
- First-hop virtual gateway (10.10.10.254, 10.10.20.254, 2001:db8:10::254) does not respond to ICMP.
- End hosts lose default gateway and cannot reach core network.
- Virtual MAC address 00:1c:73:00:00:01 missing from switch forwarding tables.

## Diagnostic Checks
1. Query VARP status: `show ip virtual-router`
2. Query VRRP status: `show vrrp`
3. Check sub-interface configuration: `show running-config interface Ethernet2.10`
4. Inspect ARP entries: `show ip arp`

## Remediation & Recovery
1. Ensure virtual-router MAC and IP are configured and interface is un-shut:
   ```
   configure
   ip virtual-router mac-address 00:1c:73:00:00:01
   interface Ethernet2.10
      no shutdown
      ip virtual-router address 10.10.10.254
   end
   write memory
   ```
2. Verify virtual router state is active and responding.
3. Verify synthetic probes from hosts to Gateway succeed.
