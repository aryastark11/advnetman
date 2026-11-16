# Runbook: VLAN Trunk Missing / Layer 2 Trunk Disconnection

## Symptoms
- End hosts in specific VLANs cannot communicate across switches or reach their gateway.
- Inter-switch trunk ports missing allowed VLANs (e.g. VLAN 10 or 20 pruned).
- ARP requests broadcast on access ports receive no response.

## Diagnostic Checks
1. Query switchport trunk configuration: `show interfaces trunk`
2. Check interface status: `show interfaces status`
3. Inspect VLAN database: `show vlan`
4. Inspect MAC address table: `show mac address-table`

## Remediation & Recovery
1. Add required VLANs to trunk allowed list:
   ```
   configure
   interface <trunk_interface>
      switchport mode trunk
      switchport trunk allowed vlan add 10,20,30
   end
   write memory
   ```
2. Verify trunk includes VLANs in `show interfaces trunk`.
3. Verify host ARP resolves and pings pass.
