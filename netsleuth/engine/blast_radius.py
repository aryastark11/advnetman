from typing import Dict, List, Any, Set
import networkx as nx
from netsleuth.graph.topology import topology

def compute_blast_radius(root_cause_device: str, category: str, details: Dict[str, Any]) -> Dict[str, Any]:
    norm_dev = root_cause_device.upper() if root_cause_device else ""
    affected_hosts: Set[str] = set()
    affected_services: Set[str] = set()
    impact_level = "low"

    # 1. Web Server / Internet Edge Outage
    if norm_dev in ["WEB-SERVER", "WEB SERVER", "R5"] or "Web Server" in category or "BGP" in category:
        # Check if R5 is completely isolated or web-server down
        affected_hosts = {"H1", "H2", "H3", "H4", "H5", "H6", "H7"}
        affected_services = {
            "Internet Web Access (198.51.100.10:80)",
            "External HTTP Hello-World Service",
            "Internet Transit Peering"
        }
        impact_level = "critical"

    # 2. Area 10 / Branch Outage (R6, R7, H5)
    elif norm_dev in ["R6", "R7", "H5"] or "Area 10" in str(details) or "Area 20" in str(details):
        affected_hosts = {"H5"}
        affected_services = {
            "H5 VLAN 10 Corporate Data",
            "H5 to Internet Transit",
            "OSPF Area 10 Backbone Routing"
        }
        impact_level = "high"

    # 3. Area 30 / Branch Outage (R8, S5, H6, H7)
    elif norm_dev in ["R8", "S5", "H6", "H7"] or "Area 30" in str(details):
        affected_hosts = {"H6", "H7"}
        affected_services = {
            "H6/H7 VLAN 10 Campus Access",
            "H6/H7 to Internet Transit",
            "OSPF Area 30 Backbone Routing",
            "ZTP Expansion Network"
        }
        impact_level = "high"

    # 4. Campus Access Layer S1 (H1, H2)
    elif norm_dev == "S1":
        affected_hosts = {"H1", "H2"}
        affected_services = {
            "VLAN 10 Corporate Data (H1)",
            "VLAN 20 Voice/IoT (H2)",
            "Campus Access Switching"
        }
        impact_level = "high"

    # 5. Campus Access Layer S2 (H3, H4)
    elif norm_dev == "S2":
        affected_hosts = {"H3", "H4"}
        affected_services = {
            "VLAN 10 Corporate Data (H3)",
            "VLAN 30 IPv6 Services (H4)",
            "Campus Access Switching"
        }
        impact_level = "high"

    # 6. Distribution Layer R1 / R2 (VARP / RIPv2)
    elif norm_dev in ["R1", "R2"]:
        if "VARP" in category or "VRRP" in category:
            affected_hosts = {"H1", "H2", "H3", "H4"}
            affected_services = {
                "VARP Active-Active Gateway Redundancy",
                "Default Gateway 10.10.10.254 (VLAN 10)",
                "Default Gateway 10.10.20.254 (VLAN 20)"
            }
            impact_level = "medium"
        else:
            affected_hosts = {"H1", "H2"} if norm_dev == "R1" else {"H3", "H4"}
            affected_services = {
                f"{norm_dev} Core Transit Routing",
                "RIPv2 Campus Subnet Distribution"
            }
            impact_level = "high"

    # 7. Core Layer S3, S4, R3, R4
    elif norm_dev in ["S3", "S4", "R3", "R4"]:
        affected_hosts = {"H1", "H2", "H3", "H4"}
        affected_services = {
            "OSPF Area 0 Backbone Transit",
            "Core ECMP Redundancy Path"
        }
        impact_level = "medium"

    # 8. NMAS
    elif norm_dev in ["NMAS", "BACKUP-SERVER"]:
        affected_services = {
            "Telemetry & Data Lake Ingestion",
            "Automated CI/CD Pipeline Execution",
            "Isolated Disaster Recovery Backup"
        }
        impact_level = "medium"

    else:
        affected_hosts = set()
        affected_services = {"Network Management & Telemetry"}
        impact_level = "low"

    return {
        "impact_level": impact_level,
        "affected_hosts": sorted(list(affected_hosts)),
        "affected_services": sorted(list(affected_services)),
        "total_hosts_affected": len(affected_hosts),
        "total_services_affected": len(affected_services)
    }
