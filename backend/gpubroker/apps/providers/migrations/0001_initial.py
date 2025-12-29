# Generated migration for providers models
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
            name="Provider",
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
                ("name", models.CharField(max_length=100, unique=True)),
                ("display_name", models.CharField(max_length=100)),
                ("website_url", models.URLField(blank=True, max_length=500, null=True)),
                ("api_base_url", models.URLField(max_length=500)),
                ("documentation_url", models.URLField(blank=True, max_length=500, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("maintenance", "Maintenance"),
                            ("deprecated", "Deprecated"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "supported_regions",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=50),
                        blank=True,
                        default=list,
                        size=None,
                    ),
                ),
                (
                    "compliance_tags",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=50),
                        blank=True,
                        default=list,
                        size=None,
                    ),
                ),
                (
                    "reliability_score",
                    models.DecimalField(decimal_places=2, default=0.5, max_digits=3),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Provider",
                "verbose_name_plural": "Providers",
                "db_table": "providers",
                "ordering": ["display_name"],
            },
        ),
        migrations.CreateModel(
            name="GPUOffer",
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
                ("external_id", models.CharField(max_length=255)),
                ("name", models.CharField(blank=True, max_length=255, null=True)),
                ("gpu_type", models.CharField(max_length=100)),
                ("gpu_memory_gb", models.IntegerField()),
                ("cpu_cores", models.IntegerField()),
                ("ram_gb", models.IntegerField()),
                ("storage_gb", models.IntegerField()),
                (
                    "storage_type",
                    models.CharField(
                        choices=[("SSD", "SSD"), ("NVMe", "NVMe"), ("HDD", "HDD")],
                        default="SSD",
                        max_length=20,
                    ),
                ),
                ("price_per_hour", models.DecimalField(decimal_places=4, max_digits=8)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("region", models.CharField(max_length=50)),
                ("availability_zone", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "availability_status",
                    models.CharField(
                        choices=[
                            ("available", "Available"),
                            ("limited", "Limited"),
                            ("unavailable", "Unavailable"),
                        ],
                        default="available",
                        max_length=20,
                    ),
                ),
                ("min_rental_time", models.IntegerField(default=1)),
                ("max_rental_time", models.IntegerField(blank=True, null=True)),
                ("spot_pricing", models.BooleanField(default=False)),
                ("preemptible", models.BooleanField(default=False)),
                ("sla_uptime", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("network_speed_gbps", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                (
                    "compliance_tags",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=50),
                        blank=True,
                        default=list,
                        size=None,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offers",
                        to="providers.provider",
                    ),
                ),
            ],
            options={
                "verbose_name": "GPU Offer",
                "verbose_name_plural": "GPU Offers",
                "db_table": "gpu_offers",
                "ordering": ["price_per_hour"],
                "unique_together": {("provider", "external_id")},
            },
        ),
        migrations.CreateModel(
            name="PriceHistory",
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
                ("price_per_hour", models.DecimalField(decimal_places=4, max_digits=8)),
                ("availability_status", models.CharField(max_length=20)),
                ("recorded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="price_history",
                        to="providers.gpuoffer",
                    ),
                ),
            ],
            options={
                "verbose_name": "Price History",
                "verbose_name_plural": "Price History",
                "db_table": "price_history",
                "ordering": ["-recorded_at"],
            },
        ),
        migrations.CreateModel(
            name="KPICalculation",
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
                (
                    "calculation_type",
                    models.CharField(
                        choices=[
                            ("cost_per_token", "Cost per Token"),
                            ("cost_per_gflop", "Cost per GFLOP"),
                            ("efficiency_score", "Efficiency Score"),
                        ],
                        max_length=50,
                    ),
                ),
                ("value", models.DecimalField(decimal_places=6, max_digits=12)),
                ("metadata", models.JSONField(default=dict)),
                ("calculated_at", models.DateTimeField(auto_now_add=True)),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kpi_calculations",
                        to="providers.gpuoffer",
                    ),
                ),
            ],
            options={
                "verbose_name": "KPI Calculation",
                "verbose_name_plural": "KPI Calculations",
                "db_table": "kpi_calculations",
                "ordering": ["-calculated_at"],
                "unique_together": {("offer", "calculation_type")},
            },
        ),
        migrations.CreateModel(
            name="ProviderHealthCheck",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("healthy", "Healthy"),
                            ("degraded", "Degraded"),
                            ("down", "Down"),
                            ("error", "Error"),
                        ],
                        max_length=20,
                    ),
                ),
                ("response_time_ms", models.IntegerField()),
                ("error_message", models.TextField(blank=True, null=True)),
                ("checked_at", models.DateTimeField(auto_now_add=True)),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="health_checks",
                        to="providers.provider",
                    ),
                ),
            ],
            options={
                "verbose_name": "Provider Health Check",
                "verbose_name_plural": "Provider Health Checks",
                "db_table": "provider_health_checks",
                "ordering": ["-checked_at"],
            },
        ),
        migrations.AddIndex(
            model_name="gpuoffer",
            index=models.Index(fields=["gpu_type"], name="gpu_offers_gpu_typ_idx"),
        ),
        migrations.AddIndex(
            model_name="gpuoffer",
            index=models.Index(fields=["region"], name="gpu_offers_region_idx"),
        ),
        migrations.AddIndex(
            model_name="gpuoffer",
            index=models.Index(fields=["price_per_hour"], name="gpu_offers_price_idx"),
        ),
        migrations.AddIndex(
            model_name="gpuoffer",
            index=models.Index(fields=["availability_status"], name="gpu_offers_avail_idx"),
        ),
        migrations.AddIndex(
            model_name="pricehistory",
            index=models.Index(fields=["offer", "recorded_at"], name="price_hist_offer_idx"),
        ),
    ]
