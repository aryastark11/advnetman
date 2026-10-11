# Policy: network-operator
# Grants read/write access to network device secrets, explicitly denies NMAS host secrets.

path "network/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "network/data/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "network/metadata/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
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
