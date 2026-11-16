# Runbook: Web Server Down / HTTP Service Outage

## Symptoms
- HTTP probes from all hosts to 198.51.100.10 return connection refused, timeout, or 50x.
- Web server container service (nginx or python HTTP server) is stopped or failing.
- Edge router R5 link to Web Server is down or dropping packets.

## Diagnostic Checks
1. Check Web Server container process status: `docker exec clab-lab1-web-server ps aux`
2. Test local HTTP response on web server: `docker exec clab-lab1-web-server curl -s -m 2 http://127.0.0.1:80`
3. Inspect Web Server web service logs: `docker logs clab-lab1-web-server`
4. Check edge interface on R5: `show interfaces Ethernet1`

## Remediation & Recovery
1. Start/restart the web service process inside the web-server container:
   ```
   docker exec clab-lab1-web-server /bin/bash /start.sh
   ```
   Or on R5 if interface Ethernet1 is down:
   ```
   configure
   interface Ethernet1
      no shutdown
   end
   write memory
   ```
2. Verify HTTP 200 GET returns `Hello World` from all hosts.
3. Verify synthetic probes recover across all hosts.
