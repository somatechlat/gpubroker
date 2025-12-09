# ============================================
# HashiCorp Vault Configuration
# GPUBROKER - Enterprise Secret Management
# ============================================

# Storage backend - file for dev, use Consul/Raft for production
storage "file" {
  path = "/vault/data"
}

# Listener configuration
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true  # Enable TLS in production!
}

# API address
api_addr = "http://0.0.0.0:8200"

# Disable mlock for Docker (enable in production with proper capabilities)
disable_mlock = true

# UI enabled for development
ui = true

# Logging
log_level = "info"

# Max lease TTL
max_lease_ttl = "768h"
default_lease_ttl = "768h"
