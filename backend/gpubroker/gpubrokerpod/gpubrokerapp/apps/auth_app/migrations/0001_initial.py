# Generated migration for auth_app models
# managed=True for test database creation

import django.contrib.postgres.fields
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("email", models.EmailField(max_length=255, unique=True)),
                (
                    "password_hash",
                    models.CharField(db_column="password_hash", max_length=255),
                ),
                ("full_name", models.CharField(max_length=255)),
                (
                    "organization",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("is_verified", models.BooleanField(default=False)),
                ("is_staff", models.BooleanField(default=False)),
                ("is_superuser", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_login", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "User",
                "verbose_name_plural": "Users",
                "db_table": "users",
            },
        ),
        migrations.CreateModel(
            name="UserSession",
            fields=[
                (
                    "jti",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("refresh_token_hash", models.CharField(max_length=255)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to="auth_app.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "User Session",
                "verbose_name_plural": "User Sessions",
                "db_table": "user_sessions",
            },
        ),
        migrations.CreateModel(
            name="APIKey",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("key_hash", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=100)),
                (
                    "scopes",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=50),
                        blank=True,
                        default=list,
                        size=None,
                    ),
                ),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_keys",
                        to="auth_app.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "API Key",
                "verbose_name_plural": "API Keys",
                "db_table": "api_keys",
            },
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("event_type", models.CharField(max_length=50)),
                (
                    "resource_type",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                ("resource_id", models.UUIDField(blank=True, null=True)),
                ("event_data", models.JSONField(default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "previous_hash",
                    models.CharField(blank=True, max_length=64, null=True),
                ),
                (
                    "current_hash",
                    models.CharField(blank=True, max_length=64, null=True),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="auth_app.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Audit Log",
                "verbose_name_plural": "Audit Logs",
                "db_table": "audit_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SavedSearch",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("search_filters", models.JSONField()),
                ("is_alert", models.BooleanField(default=False)),
                (
                    "alert_threshold",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=8, null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_searches",
                        to="auth_app.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Saved Search",
                "verbose_name_plural": "Saved Searches",
                "db_table": "saved_searches",
            },
        ),
        migrations.CreateModel(
            name="UserPreference",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("preference_key", models.CharField(max_length=100)),
                ("preference_value", models.JSONField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preferences",
                        to="auth_app.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "User Preference",
                "verbose_name_plural": "User Preferences",
                "db_table": "user_preferences",
                "unique_together": {("user", "preference_key")},
            },
        ),
    ]
