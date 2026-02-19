"""
Django management command to initialize configuration from Vault.
Follows Django ORM standards - stores all config in database.

Usage:
    python manage.py init_config_from_vault
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from shared.models.configuration import (
    Configuration,
    DatabaseConfiguration,
    CacheConfiguration,
    ServiceConfiguration,
)
import os
import requests


class Command(BaseCommand):
    help = 'Initialize configuration from Vault into Django database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--vault-addr',
            type=str,
            default=os.environ.get('VAULT_ADDR', 'http://localhost:28005'),
            help='Vault address'
        )
        parser.add_argument(
            '--vault-token',
            type=str,
            default=os.environ.get('VAULT_TOKEN', 'root'),
            help='Vault token'
        )
    
    def handle(self, *args, **options):
        vault_addr = options['vault_addr']
        vault_token = options['vault_token']
        
        self.stdout.write(self.style.SUCCESS('🔐 Initializing configuration from Vault...'))
        
        try:
            # Test Vault connection
            self.stdout.write('Testing Vault connection...')
            response = requests.get(
                f"{vault_addr}/v1/sys/health",
                timeout=10
            )
            response.raise_for_status()
            self.stdout.write(self.style.SUCCESS('✅ Vault is accessible'))
            
            # Fetch secrets from Vault
            headers = {'X-Vault-Token': vault_token}
            
            with transaction.atomic():
                # Database configuration
                self.stdout.write('Fetching database configuration...')
                db_secret = self._get_vault_secret(
                    vault_addr, headers, 'secret/data/database/postgres'
                )
                
                if db_secret:
                    DatabaseConfiguration.objects.update_or_create(
                        name='default',
                        defaults={
                            'engine': 'django.db.backends.postgresql',
                            'host': db_secret.get('host', 'postgres'),
                            'port': int(db_secret.get('port', 5432)),
                            'database': db_secret.get('database', 'gpubroker'),
                            'username': db_secret.get('username', 'gpubroker'),
                            'password': db_secret.get('password'),
                            'is_active': True,
                        }
                    )
                    self.stdout.write(self.style.SUCCESS('✅ Database configuration stored'))
                
                # Cache configuration
                self.stdout.write('Fetching cache configuration...')
                redis_secret = self._get_vault_secret(
                    vault_addr, headers, 'secret/data/database/redis'
                )
                
                if redis_secret:
                    CacheConfiguration.objects.update_or_create(
                        name='default',
                        defaults={
                            'backend': 'django_redis.cache.RedisCache',
                            'host': redis_secret.get('host', 'redis'),
                            'port': int(redis_secret.get('port', 6379)),
                            'db': 0,
                            'password': redis_secret.get('password'),
                            'is_active': True,
                        }
                    )
                    self.stdout.write(self.style.SUCCESS('✅ Cache configuration stored'))
                
                # Django secret key
                self.stdout.write('Fetching Django configuration...')
                django_secret = self._get_vault_secret(
                    vault_addr, headers, 'secret/data/django/config'
                )
                
                if django_secret:
                    Configuration.objects.set_value(
                        key='django.secret_key',
                        value=django_secret.get('secret_key'),
                        is_secret=True,
                        description='Django SECRET_KEY'
                    )
                    self.stdout.write(self.style.SUCCESS('✅ Django configuration stored'))
                
                # JWT configuration
                self.stdout.write('Fetching JWT configuration...')
                jwt_secret = self._get_vault_secret(
                    vault_addr, headers, 'secret/data/jwt/keys'
                )
                
                if jwt_secret:
                    Configuration.objects.set_value(
                        key='jwt.private_key',
                        value=jwt_secret.get('private_key'),
                        is_secret=True,
                        description='JWT private key'
                    )
                    Configuration.objects.set_value(
                        key='jwt.public_key',
                        value=jwt_secret.get('public_key'),
                        is_secret=True,
                        description='JWT public key'
                    )
                    self.stdout.write(self.style.SUCCESS('✅ JWT configuration stored'))
            
            self.stdout.write(self.style.SUCCESS('\n✅ Configuration initialized successfully!'))
            self.stdout.write(self.style.SUCCESS('All secrets are now stored in Django database (encrypted)'))
            self.stdout.write(self.style.WARNING('\n⚠️  You can now remove Vault environment variables'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to initialize configuration: {e}'))
            raise
    
    def _get_vault_secret(self, vault_addr, headers, path):
        """Fetch secret from Vault."""
        try:
            response = requests.get(
                f"{vault_addr}/v1/{path}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('data', {})
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Could not fetch {path}: {e}'))
            return None
