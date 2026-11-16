# Runbook: OSPF Area Mismatch / Neighbor Adjacency Failure

## Symptoms
- OSPF neighbor adjacency drops or fails to reach `FULL` state.
- Neighbor stays in `INIT`, `2-WAY`, or drops entirely.
- Routes across the area boundary are withdrawn from the IP routing table.

## Diagnostic Checks
1. Query OSPF neighbor status: `show ip ospf neighbor`
2. Inspect OSPF interface configuration: `show ip ospf interface <interface_name>`
3. Check syslog for OSPF mismatch warnings: `show logging 25` for `%OSPF-4-ERR_AREA_MISMATCH` or `%OSPF-4-ERR_HELLO_DEAD_MISMATCH`.
4. Check running config under interface: `show running-config interface <interface_name>`

## Remediation & Recovery
1. Configure matching OSPF area and timers:
   ```
   configure
   interface <interface_name>
      ip ospf area <expected_area>
      ip ospf hello-interval 1
      ip ospf dead-interval 3
      no shutdown
   end
   write memory
   ```
2. Verify neighbor transitions through `EXSTART` -> `EXCHANGE` -> `LOADING` -> `FULL`.
3. Verify routes re-populate in `show ip route ospf`.
