# Generated migration for shared app configuration models

from django.db import migrations, models
import encrypted_model_fields.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(db_index=True, help_text="Configuration key (e.g., 'database.postgres.host')", max_length=255, unique=True)),
                ('category', models.CharField(choices=[('database', 'Database'), ('cache', 'Cache'), ('security', 'Security'), ('api', 'API'), ('feature', 'Feature Flag'), ('service', 'External Service'), ('monitoring', 'Monitoring')], db_index=True, default='feature', help_text='Configuration category', max_length=50)),
                ('value', models.TextField(blank=True, help_text='Plain text value (for non-sensitive data)', null=True)),
                ('encrypted_value', encrypted_model_fields.fields.EncryptedTextField(blank=True, help_text='Encrypted value (for sensitive data like passwords, API keys)', null=True)),
                ('is_secret', models.BooleanField(default=False, help_text='Whether this is a secret (uses encrypted_value)')),
                ('description', models.TextField(blank=True, help_text='Human-readable description of this configuration')),
                ('is_active', models.BooleanField(db_index=True, default=True, help_text='Whether this configuration is active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuration',
                'verbose_name_plural': 'Configurations',
                'db_table': 'configuration',
                'ordering': ['category', 'key'],
            },
        ),
        migrations.CreateModel(
            name='DatabaseConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Database connection name (e.g., 'default', 'analytics')", max_length=100, unique=True)),
                ('engine', models.CharField(default='django.db.backends.postgresql', help_text='Django database engine', max_length=200)),
                ('host', models.CharField(max_length=255)),
                ('port', models.IntegerField(default=5432)),
                ('database', models.CharField(max_length=255)),
                ('username', models.CharField(max_length=255)),
                ('password', encrypted_model_fields.fields.EncryptedCharField(help_text='Encrypted database password', max_length=255)),
                ('conn_max_age', models.IntegerField(default=60, help_text='Connection max age in seconds')),
                ('ssl_mode', models.CharField(default='require', help_text='SSL mode (disable, allow, prefer, require, verify-ca, verify-full)', max_length=50)),
                ('connect_timeout', models.IntegerField(default=60, help_text='Connection timeout in seconds')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Database Configuration',
                'verbose_name_plural': 'Database Configurations',
                'db_table': 'database_configuration',
            },
        ),
        migrations.CreateModel(
            name='CacheConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Cache connection name (e.g., 'default', 'sessions')", max_length=100, unique=True)),
                ('backend', models.CharField(default='django_redis.cache.RedisCache', help_text='Django cache backend', max_length=200)),
                ('host', models.CharField(max_length=255)),
                ('port', models.IntegerField(default=6379)),
                ('db', models.IntegerField(default=0)),
                ('password', encrypted_model_fields.fields.EncryptedCharField(blank=True, help_text='Encrypted Redis password', max_length=255, null=True)),
                ('max_connections', models.IntegerField(default=50)),
                ('socket_timeout', models.IntegerField(default=5)),
                ('socket_connect_timeout', models.IntegerField(default=5)),
                ('key_prefix', models.CharField(default='gpubroker', help_text='Cache key prefix', max_length=100)),
                ('timeout', models.IntegerField(default=300, help_text='Default cache timeout in seconds')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Cache Configuration',
                'verbose_name_plural': 'Cache Configurations',
                'db_table': 'cache_configuration',
            },
        ),
        migrations.CreateModel(
            name='ServiceConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(choices=[('stripe', 'Stripe'), ('aws', 'AWS'), ('sendgrid', 'SendGrid'), ('sentry', 'Sentry'), ('prometheus', 'Prometheus')], help_text='External service name', max_length=100, unique=True)),
                ('api_key', encrypted_model_fields.fields.EncryptedTextField(help_text='Encrypted API key')),
                ('api_secret', encrypted_model_fields.fields.EncryptedTextField(blank=True, help_text='Encrypted API secret (if required)', null=True)),
                ('endpoint_url', models.URLField(blank=True, help_text='Service endpoint URL', null=True)),
                ('config_json', models.JSONField(default=dict, help_text='Additional service-specific configuration')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Service Configuration',
                'verbose_name_plural': 'Service Configurations',
                'db_table': 'service_configuration',
            },
        ),
        migrations.AddIndex(
            model_name='configuration',
            index=models.Index(fields=['key', 'is_active'], name='configurati_key_b8f4e7_idx'),
        ),
        migrations.AddIndex(
            model_name='configuration',
            index=models.Index(fields=['category', 'is_active'], name='configurati_categor_c5e8a9_idx'),
        ),
    ]
