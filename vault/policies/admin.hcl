# Policy: admin
# Full administrative access across all mounts and system configurations.

path "*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
