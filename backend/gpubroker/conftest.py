"""
Pytest configuration and fixtures for GPUBROKER Django tests.

Provides shared fixtures for:
- Django test client
- Authenticated users and JWT tokens
- Database objects (providers, offers, benchmarks)
"""
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Tuple

import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gpubroker.settings.test')

import django
django.setup()

# Patch models to be managed for testing
from django.apps import apps
for model in apps.get_models():
    model._meta.managed = True


# ============================================
# Database Fixtures
# ============================================

@pytest.fixture
def test_user(db):
    """Create a test user."""
    from apps.auth_app.models import User
    
    user = User.objects.create(
        id=uuid.uuid4(),
        email='test@example.com',
        password_hash='$argon2id$v=19$m=65536,t=3,p=4$test',
        full_name='Test User',
        organization='Test Org',
        is_active=True,
        is_verified=True,
    )
    return user


@pytest.fixture
def test_user_tokens(test_user) -> Tuple[str, str]:
    """Create JWT tokens for test user."""
    from apps.auth_app.auth import create_access_token, create_refresh_token
    
    token_data = {
        'sub': test_user.email,
        'roles': ['user'],
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return access_token, refresh_token


@pytest.fixture
def auth_headers(test_user_tokens) -> Dict[str, str]:
    """HTTP headers with JWT authentication."""
    access_token, _ = test_user_tokens
    return {'Authorization': f'Bearer {access_token}'}


@pytest.fixture
def test_provider(db):
    """Create a test provider."""
    from apps.providers.models import Provider
    
    provider = Provider.objects.create(
        id=uuid.uuid4(),
        name='test_provider',
        display_name='Test Provider',
        api_base_url='https://api.testprovider.com',
        status='active',
        reliability_score=Decimal('0.95'),
    )
    return provider


@pytest.fixture
def test_gpu_offers(db, test_provider):
    """Create test GPU offers."""
    from apps.providers.models import GPUOffer
    
    offers = []
    gpu_types = [
        ('RTX 4090', 24, '1.50'),
        ('A100', 80, '3.50'),
        ('H100', 80, '4.50'),
        ('RTX 3080', 10, '0.50'),
    ]
    
    for gpu_type, memory, price in gpu_types:
        offer = GPUOffer.objects.create(
            id=uuid.uuid4(),
            provider=test_provider,
            external_id=f'{test_provider.name}:{gpu_type}:us-east-1',
            name=f'{gpu_type} Instance',
            gpu_type=gpu_type,
            gpu_memory_gb=memory,
            cpu_cores=8,
            ram_gb=32,
            storage_gb=100,
            price_per_hour=Decimal(price),
            currency='USD',
            region='us-east-1',
            availability_status='available',
            compliance_tags=['soc2', 'gdpr'],
        )
        offers.append(offer)
    
    return offers


@pytest.fixture
def test_benchmark(db):
    """Create a test GPU benchmark."""
    from apps.math_core.models import GPUBenchmark
    
    benchmark = GPUBenchmark.objects.create(
        id=uuid.uuid4(),
        gpu_model='RTX 4090',
        tflops_fp32=82.6,
        tflops_fp16=165.2,
        tflops_int8=330.4,
        memory_bandwidth_gbps=1008,
        vram_gb=24,
        tokens_per_second_7b=1100,
        tokens_per_second_13b=650,
        tokens_per_second_70b=120,
        image_gen_per_minute=45,
        source='nvidia_official',
    )
    return benchmark


# ============================================
# Client Fixtures
# ============================================

@pytest.fixture
def client():
    """Django test client."""
    from django.test import Client
    return Client()


@pytest.fixture
def async_client():
    """Django async test client."""
    from django.test import AsyncClient
    return AsyncClient()


@pytest.fixture
def api_client():
    """Django Ninja test client for API v2."""
    from ninja.testing import TestAsyncClient
    from gpubroker.api.v2 import api
    return TestAsyncClient(api)


# ============================================
# Service Fixtures
# ============================================

@pytest.fixture
def kpi_calculator():
    """KPI Calculator instance."""
    from apps.math_core.services import KPICalculator
    return KPICalculator()


@pytest.fixture
def workload_mapper():
    """Workload Mapper instance."""
    from apps.math_core.services import WorkloadMapper
    return WorkloadMapper()


@pytest.fixture
def topsis_engine():
    """TOPSIS Engine instance."""
    from apps.math_core.algorithms.topsis import TOPSISEngine
    return TOPSISEngine()


# ============================================
# Utility Fixtures
# ============================================

@pytest.fixture
def sample_decision_matrix():
    """Sample decision matrix for TOPSIS tests."""
    import numpy as np
    return np.array([
        [1.50, 24, 82.6, 0.95, 0.90],   # RTX 4090
        [3.50, 80, 19.5, 0.85, 0.95],   # A100
        [4.50, 80, 51.0, 0.80, 0.98],   # H100
        [0.50, 10, 29.8, 0.99, 0.85],   # RTX 3080
    ])


@pytest.fixture
def sample_weights():
    """Sample weights for TOPSIS (must sum to 1.0)."""
    return [0.30, 0.25, 0.20, 0.15, 0.10]


@pytest.fixture
def sample_criteria_types():
    """Sample criteria types for TOPSIS."""
    return ['cost', 'benefit', 'benefit', 'benefit', 'benefit']
