#!/usr/bin/env bash
# ==============================================================================
# Script: ping_h5_to_internet.sh
# Purpose: Execute end-to-end ping, traceroute, and HTTP validation from Host H5
#          to the simulated public Internet Web Server (198.51.100.10).
# ==============================================================================
set -euo pipefail

TARGET_IP="198.51.100.10"
CONTAINER_NAME="clab-lab1-h5"
PING_COUNT="${1:-4}"

echo "=============================================================================="
echo "   PING & INTERNET REACHABILITY TEST: H5 (VLAN 10) -> PUBLIC INTERNET        "
echo "=============================================================================="
echo "Source Host:         $CONTAINER_NAME (10.70.10.105 via R7 Ethernet2.10)"
echo "Destination Target:  $TARGET_IP (Internet Public Web Server)"
echo "Ping Count:          $PING_COUNT packets"
echo "=============================================================================="
echo ""

# 1. ICMP Ping Execution
echo "[Step 1/3] Executing ICMP Ping from H5 to Internet ($TARGET_IP)..."
docker exec "$CONTAINER_NAME" ping -c "$PING_COUNT" -W 2 "$TARGET_IP"
echo ""

# 2. Layer 3 Hop-by-Hop Traceroute
echo "[Step 2/3] Performing hop-by-hop traceroute to trace transit routing path..."
docker exec "$CONTAINER_NAME" traceroute -n "$TARGET_IP"
echo ""

# 3. Layer 7 HTTP Service Validation
echo "[Step 3/3] Validating HTTP GET response from Internet Web Server..."
HTTP_STATUS=$(docker exec "$CONTAINER_NAME" curl -s -o /dev/null -w "%{http_code}" -m 5 "http://$TARGET_IP")
if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "  [✓ SUCCESS] HTTP 200 OK received from http://$TARGET_IP"
    docker exec "$CONTAINER_NAME" curl -s -m 5 "http://$TARGET_IP" | grep -E "<h1>|<h2>|<p>" | head -n 4 | sed 's/^/      /'
else
    echo "  [✗ FAILURE] Unexpected HTTP status code: $HTTP_STATUS"
    exit 1
fi

echo ""
echo "=============================================================================="
echo "  [✓] ALL INTERNET CONNECTIVITY CHECKS PASSED FOR HOST H5 (100% REACHABLE)  "
echo "=============================================================================="
