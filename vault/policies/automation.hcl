# Policy: automation
# Least-privilege policy for CI/CD runners and password rotation scripts.

path "network/data/devices/*" {
  capabilities = ["create", "read", "update", "list"]
}

path "network/metadata/devices/*" {
  capabilities = ["read", "list"]
}

# Explicit Deny on NMAS Admin Secrets Mount
path "nmas-admin/*" {
  capabilities = ["deny"]
}

path "nmas-admin/data/*" {
  capabilities = ["deny"]
}

path "nmas-admin/metadata/*" {
  capabilities = ["deny"]
}
