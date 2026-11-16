# Runbook: Interface Down / Physical Link Failure

## Symptoms
- Node interface reports lineProtocolStatus `down` or `notconnect`.
- Probes traversing the link fail with packet loss or timeout.
- Adjacencies (OSPF, BGP, or LLDP) across the link drop.

## Diagnostic Checks
1. Query interface status: `show interfaces status`
2. Check interface error counters: `show interfaces counters errors`
3. Inspect system log: `show logging 20` for `%LINK-5-CHANGED` or `%LINEPROTO-5-UPDOWN` events.
4. Validate physical LLDP neighbor: `show lldp neighbors`

## Remediation & Recovery
1. Re-enable the administrative interface state:
   ```
   configure
   interface <interface_name>
      no shutdown
   end
   write memory
   ```
2. Verify interface transitions to `connected` and line protocol `up`.
3. Verify synthetic probes recover.
