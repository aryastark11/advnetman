# Runbook: RIP Missing Network / Routing Advertisement Failure

## Symptoms
- Router database does not contain expected customer or VLAN subnets (10.10.x.x).
- End hosts cannot route packets beyond their local first-hop gateway.
- Inter-VLAN or host-to-WAN traffic drops at distribution switches.

## Diagnostic Checks
1. Inspect RIP route database: `show ip rip database`
2. Inspect active RIP routing protocol configuration: `show running-config section router rip`
3. Verify connected interfaces in the subnet: `show ip interface brief`

## Remediation & Recovery
1. Add missing network statement under router rip:
   ```
   configure
   router rip
      network 10.10.0.0/16
      no shutdown
   end
   write memory
   ```
2. Verify subnets appear in `show ip rip database`.
3. Verify synthetic pings from hosts resume.
