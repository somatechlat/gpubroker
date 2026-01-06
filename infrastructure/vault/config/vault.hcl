# ============================================
# HashiCorp Vault Configuration
# GPUBROKER - Production-Grade Secret Management
# Memory-Optimized for 256MB Container
# ============================================

# Storage backend - file for dev, use Consul/Raft for production
storage "file" {
  path = "/vault/data"
}

# Listener configuration
listener "tcp" {
  address         = "0.0.0.0:18280"
  tls_disable     = true  # Enable TLS in production!
  
  # Telemetry
  telemetry {
    unauthenticated_metrics_access = true
  }
}

# API address
api_addr     = "http://0.0.0.0:18280"
cluster_addr = "http://0.0.0.0:18281"

# Disable mlock for Docker (enable in production with proper capabilities)
disable_mlock = true

# UI enabled for development
ui = true

# Logging
log_level = "info"
log_format = "json"

# Lease TTL
max_lease_ttl     = "768h"
default_lease_ttl = "768h"

# Telemetry for Prometheus
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname          = true
}

# Performance tuning (memory-optimized)
cache_size = 32000

# Seal configuration (auto-unseal in production)
# seal "awskms" {
#   region     = "us-east-1"
#   kms_key_id = "alias/vault-unseal-key"
# }
