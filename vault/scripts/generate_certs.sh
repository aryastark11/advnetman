#!/bin/bash
set -e
CERTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../certs"
mkdir -p "$CERTS_DIR"

echo "Generating local Certificate Authority (CA)..."
openssl req -x509 -new -nodes -keyout "$CERTS_DIR/ca.key" -out "$CERTS_DIR/ca.crt" -days 3650 \
  -subj "/C=US/ST=Colorado/L=Boulder/O=CSCI5840 Lab/OU=NMAS Security/CN=CSCI5840 Root CA"

echo "Generating Vault server key and CSR..."
openssl req -new -nodes -keyout "$CERTS_DIR/vault.key" -out "$CERTS_DIR/vault.csr" \
  -subj "/C=US/ST=Colorado/L=Boulder/O=CSCI5840 Lab/OU=NMAS Security/CN=vault.nmas.local"

cat << 'EXT' > "$CERTS_DIR/vault.ext"
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = vault
DNS.3 = nmas
DNS.4 = vault.nmas.local
IP.1 = 127.0.0.1
IP.2 = 172.20.20.100
IP.3 = 10.99.0.100
EXT

echo "Signing Vault server certificate with CA..."
openssl x509 -req -in "$CERTS_DIR/vault.csr" -CA "$CERTS_DIR/ca.crt" -CAkey "$CERTS_DIR/ca.key" \
  -CAcreateserial -out "$CERTS_DIR/vault.crt" -days 825 -extfile "$CERTS_DIR/vault.ext"

chmod 600 "$CERTS_DIR"/*.key
chmod 644 "$CERTS_DIR"/*.crt
echo "TLS Certificate generation complete in $CERTS_DIR"
