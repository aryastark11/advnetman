#!/bin/bash
echo "=== Starting Continuous Multi-Host Zero-Downtime Ping Monitor ===" | tee -a /home/student/Desktop/lab1/continuous_pings.log
while true; do
  TS=$(date '+%Y-%m-%d %H:%M:%S')
  H1=$(docker exec clab-lab1-h1 ping -c 1 -W 1 198.51.100.10 2>&1 | grep -o 'time=[0-9.]* ms' || echo 'DROPPED')
  H2=$(docker exec clab-lab1-h2 ping -c 1 -W 1 198.51.100.10 2>&1 | grep -o 'time=[0-9.]* ms' || echo 'DROPPED')
  H3=$(docker exec clab-lab1-h3 ping -c 1 -W 1 198.51.100.10 2>&1 | grep -o 'time=[0-9.]* ms' || echo 'DROPPED')
  H4=$(docker exec clab-lab1-h4 ping -c 1 -W 1 198.51.100.10 2>&1 | grep -o 'time=[0-9.]* ms' || echo 'DROPPED')
  echo "[$TS] [PROBE] H1: $H1 | H2: $H2 | H3: $H3 | H4: $H4" | tee -a /home/student/Desktop/lab1/continuous_pings.log
  sleep 1
done
