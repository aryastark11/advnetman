# Runbook: BGP Peer Down / ASBR Session Collapse

## Symptoms
- ASBR router (R3, R4, or R5) reports BGP peer state `Active`, `Idle`, or `Connect` instead of `Established`.
- Prefix count drops to 0.
- External / WAN routes withdrawn; hosts lose internet web connectivity.

## Diagnostic Checks
1. Query BGP summary table: `show ip bgp summary`
2. Check TCP connectivity to peer IP on port 179: `show ip bgp neighbors <peer_ip>`
3. Check interface toward peer: `show interfaces status`
4. Inspect syslog: `show logging 20` for `%BGP-5-ADJCHANGE` neighbor down events.

## Remediation & Recovery
1. Re-enable neighbor and verify peer configuration:
   ```
   configure
   router bgp <asn>
      neighbor <peer_ip> remote-as <peer_asn>
      no neighbor <peer_ip> shutdown
   end
   write memory
   ```
2. Verify BGP state reaches `Established` with prefixes received > 0.
3. Verify host-to-web-server probes recover.
