import http.server
import socket
import os

os.chdir('/var/www/html')

class DualStackServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6

Handler = http.server.SimpleHTTPRequestHandler
httpd = DualStackServer(('::', 80), Handler)
print("Serving HTTP on dual-stack port 80...")
httpd.serve_forever()
