#!/usr/bin/env python3
"""
GPUBROKER Vault Setup Script
Production-Grade Secret Management Configuration

Following VIBE CODING RULES:
- NO HARDCODED SECRETS ANYWHERE
- VAULT-ONLY SECRET MANAGEMENT
- PRODUCTION SECURITY FIRST
"""

import os
import sys
import json
import hvac
import secrets
import subprocess
from pathlib import Path


class GPUBrokerVaultSetup:
    """Complete Vault setup for GPUBROKER production infrastructure."""

    def __init__(self):
        self.vault_addr = os.environ.get("VAULT_ADDR", "http://localhost:18280")
        self.vault_token = os.environ.get("VAULT_ROOT_TOKEN")

        if not self.vault_token:
            print("❌ VAULT_ROOT_TOKEN environment variable required for initial setup")
            sys.exit(1)

        try:
            self.client = hvac.Client(url=self.vault_addr, token=self.vault_token)
            # Verify connection
            self.client.sys.read_health_status()
            print(f"✅ Connected to Vault at {self.vault_addr}")
        except Exception as e:
            print(f"❌ Failed to connect to Vault: {e}")
            sys.exit(1)

    def generate_secrets(self):
        """Generate secure secrets for all services."""
        secrets_config = {
            # Django secret key
            "gpubroker/django": {
                "secret_key": secrets.token_urlsafe(50),
                "debug": False,
            },
            # Database configuration
            "gpubroker/database": {
                "url": os.environ.get(
                    "DATABASE_URL",
                    "postgresql://gpubroker:CHANGE_ME@localhost:5432/gpubroker",
                ),
                "conn_max_age": 60,
                "sslmode": "require",
                "connect_timeout": 60,
            },
            # Redis configuration
            "gpubroker/redis": {
                "url": os.environ.get(
                    "REDIS_URL", "redis://:CHANGE_ME@localhost:6379/0"
                ),
                "max_connections": 50,
                "connect_timeout": 5,
                "socket_timeout": 5,
                "health_check_interval": 30,
                "key_prefix": "gpubroker",
                "timeout": 300,
                "channel_capacity": 1500,
                "channel_expiry": 60,
                "session_age": 3600,
            },
            # JWT configuration
            "gpubroker/jwt": {
                "secret_key": secrets.token_urlsafe(64),
                "access_token_lifetime": 900,
                "refresh_token_lifetime": 86400,
                "algorithm": "HS256",
                "audience": "gpubroker-api",
                "issuer": "gpubroker-auth",
                "api_key_length": 32,
                "api_key_prefix": "gpb_",
                "anon_rate_limit": "100/hour",
                "user_rate_limit": "1000/hour",
                "login_rate_limit": "5/minute",
                "password_reset_rate_limit": "3/hour",
                "api_rate_limit": "5000/hour",
                "page_size": 50,
            },
            # External services
            "gpubroker/services": {
                "stripe_publishable_key": os.environ.get(
                    "STRIPE_PUBLISHABLE_KEY", "pk_test_CHANGE_ME"
                ),
                "stripe_secret_key": os.environ.get(
                    "STRIPE_SECRET_KEY", "sk_test_CHANGE_ME"
                ),
                "stripe_webhook_secret": os.environ.get(
                    "STRIPE_WEBHOOK_SECRET", "whsec_CHANGE_ME"
                ),
                "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID", ""),
                "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
                "aws_default_region": os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
                "email_host": os.environ.get("EMAIL_HOST", "smtp.gmail.com"),
                "email_port": os.environ.get("EMAIL_PORT", 587),
                "email_host_user": os.environ.get("EMAIL_HOST_USER", ""),
                "email_host_password": os.environ.get("EMAIL_HOST_PASSWORD", ""),
                "email_use_tls": os.environ.get("EMAIL_USE_TLS", "true").lower()
                == "true",
                "sentry_dsn": os.environ.get("SENTRY_DSN", ""),
                "prometheus_pushgateway": os.environ.get("PROMETHEUS_PUSHGATEWAY", ""),
                "cors_allowed_origins": os.environ.get(
                    "CORS_ALLOWED_ORIGINS", "https://gpubroker.com"
                ).split(","),
                "cors_allow_credentials": True,
                "cors_allowed_headers": [
                    "accept",
                    "accept-language",
                    "content-language",
                    "authorization",
                    "content-type",
                    "x-requested-with",
                ],
            },
            # Monitoring configuration
            "gpubroker/monitoring": {
                "security_monitoring_enabled": True,
                "suspicious_login_threshold": 5,
                "failed_login_attempt_limit": 10,
                "account_lockout_duration": 900,
                "security_email_recipients": os.environ.get(
                    "SECURITY_EMAIL_RECIPIENTS", "admin@gpubroker.com"
                ).split(","),
                "prometheus_enabled": True,
                "prometheus_port": 8001,
                "log_file_path": "/var/log/gpubroker/django.log",
                "security_log_file_path": "/var/log/gpubroker/security.log",
                "opentelemetry_enabled": True,
                "otel_exporter_endpoint": os.environ.get("OTEL_EXPORTER_ENDPOINT", ""),
                "otel_exporter_headers": {},
            },
            # Health check
            "gpubroker/health": {
                "status": "ok",
                "version": "1.0.0",
            },
        }

        return secrets_config

    def setup_vault_policies(self):
        """Create Vault policies for GPUBROKER."""
        policies = {
            "gpubroker-policy": """
# GPUBROKER Production Vault Policy
# Full access to gpubroker secrets with audit logging

path "secret/data/gpubroker/*" {
    capabilities = ["create", "read", "update", "delete", "list"]
}

# Allow listing policies and secrets
path "secret/metadata/gpubroker/*" {
    capabilities = ["list"]
}

# Allow renewal of tokens
path "auth/token/renew" {
    capabilities = ["update"]
}

# Allow token lookup
path "auth/token/lookup" {
    capabilities = ["read"]
}

# Allow checking own token capabilities  
path "sys/capabilities-self" {
    capabilities = ["read"]
}
            """.strip(),
        }

        for policy_name, policy_content in policies.items():
            try:
                self.client.sys.create_or_update_policy(
                    name=policy_name, rules=policy_content
                )
                print(f"✅ Created policy: {policy_name}")
            except Exception as e:
                print(f"⚠️  Policy {policy_name} may already exist: {e}")

    def setup_approle(self):
        """Create AppRole for GPUBROKER service."""
        try:
            # Create AppRole with specific settings
            role_response = self.client.auth.approle.create_role(
                name="gpubroker-role",
                token_ttl="24h",
                token_max_ttl="720h",
                token_policies=["gpubroker-policy"],
                bind_secret_id="true",
                secret_id_ttl="24h",
                secret_id_num_uses=0,  # unlimited
                secret_id_bound_cidrs=["0.0.0.0/0"],
                token_bound_cidrs=["0.0.0.0/0"],
                token_no_default_policy=True,
                token_type="service",
            )

            # Get Role ID
            role_id_response = self.client.auth.approle.read_role_id("gpubroker-role")
            role_id = role_id_response["data"]["role_id"]

            # Create Secret ID
            secret_id_response = self.client.auth.approle.generate_secret_id(
                "gpubroker-role"
            )
            secret_id = secret_id_response["data"]["secret_id"]

            print(f"✅ Created AppRole:")
            print(f"   Role ID: {role_id}")
            print(f"   Secret ID: {secret_id}")

            return role_id, secret_id

        except Exception as e:
            print(f"❌ Failed to create AppRole: {e}")
            return None, None

    def store_secrets(self, secrets_config):
        """Store all secrets in Vault."""
        for path, secret_data in secrets_config.items():
            try:
                self.client.secrets.kv.v2.create_or_update_secret(
                    path=path, secret=secret_data
                )
                print(f"✅ Stored secret: {path}")
            except Exception as e:
                print(f"❌ Failed to store secret {path}: {e}")

    def enable_secrets_engine(self):
        """Enable KV v2 secrets engine."""
        try:
            self.client.sys.enable_secrets_engine(
                backend_type="kv", path="secret", options=dict(version=2)
            )
            print("✅ Enabled KV v2 secrets engine")
        except Exception as e:
            print(f"⚠️  KV engine may already be enabled: {e}")

    def setup_audit_logging(self):
        """Enable file audit logging."""
        try:
            # Enable file audit device
            self.client.sys.enable_audit_device(
                device_type="file",
                options=dict(file_path="/var/log/vault/audit.log", mode="0640"),
            )
            print("✅ Enabled file audit logging")
        except Exception as e:
            print(f"⚠️  Audit logging may already be enabled: {e}")

    def run_setup(self):
        """Execute complete Vault setup."""
        print("🚀 Starting GPUBROKER Vault Setup")
        print("=" * 50)

        # 1. Enable secrets engine
        self.enable_secrets_engine()

        # 2. Setup policies
        self.setup_vault_policies()

        # 3. Setup AppRole
        role_id, secret_id = self.setup_approle()
        if not role_id or not secret_id:
            print("❌ AppRole setup failed")
            return False

        # 4. Generate and store secrets
        secrets_config = self.generate_secrets()
        self.store_secrets(secrets_config)

        # 5. Enable audit logging
        self.setup_audit_logging()

        print("=" * 50)
        print("✅ GPUBROKER Vault setup completed!")
        print("\n📋 Environment Variables for Production:")
        print(f"export VAULT_ADDR={self.vault_addr}")
        print(f"export VAULT_ROLE_ID={role_id}")
        print(f"export VAULT_SECRET_ID={secret_id}")
        print("\n🔐 Store these values securely in your deployment system!")
        print("\n🧪 Test with: python -m gpubroker.settings.production")

        return True


def main():
    """Main entry point."""
    setup = GPUBrokerVaultSetup()
    return setup.run_setup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
