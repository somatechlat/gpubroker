"""
Provider App Tests.

Tests for:
- Provider listing with filters
- Pagination
- Caching behavior
- Rate limiting
- Integration configuration
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from apps.providers.models import Provider, GPUOffer
from apps.providers.services import (
    list_offers_from_db,
    get_rate_limiter,
    RateLimiter,
    _cache_key,
)


# ============================================
# Rate Limiter Tests
# ============================================

class TestRateLimiter:
    """Tests for rate limiting functionality."""
    
    def test_rate_limiter_allows_within_limit(self):
        """Test rate limiter allows requests within limit."""
        limiter = RateLimiter(limit=5, window_seconds=60)
        
        for i in range(5):
            assert limiter.allow('test_key') is True
    
    def test_rate_limiter_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        limiter = RateLimiter(limit=3, window_seconds=60)
        
        # Use up the limit
        for _ in range(3):
            limiter.allow('test_key')
        
        # Next request should be blocked
        assert limiter.allow('test_key') is False
    
    def test_rate_limiter_separate_keys(self):
        """Test rate limiter tracks keys separately."""
        limiter = RateLimiter(limit=2, window_seconds=60)
        
        # Use up limit for key1
        limiter.allow('key1')
        limiter.allow('key1')
        
        # key2 should still be allowed
        assert limiter.allow('key2') is True
    
    def test_get_rate_limiter_by_plan(self):
        """Test getting rate limiter by plan."""
        free_limiter = get_rate_limiter('free')
        pro_limiter = get_rate_limiter('pro')
        
        assert free_limiter is not None
        assert pro_limiter is not None
        assert free_limiter.limit < pro_limiter.limit


# ============================================
# Cache Key Tests
# ============================================

class TestCacheKey:
    """Tests for cache key generation."""
    
    def test_cache_key_deterministic(self):
        """Test cache key is deterministic for same params."""
        params = {'gpu': 'RTX 4090', 'region': 'us-east-1'}
        
        key1 = _cache_key('/providers', params)
        key2 = _cache_key('/providers', params)
        
        assert key1 == key2
    
    def test_cache_key_different_params(self):
        """Test cache key differs for different params."""
        params1 = {'gpu': 'RTX 4090'}
        params2 = {'gpu': 'A100'}
        
        key1 = _cache_key('/providers', params1)
        key2 = _cache_key('/providers', params2)
        
        assert key1 != key2
    
    def test_cache_key_ignores_none_values(self):
        """Test cache key ignores None values."""
        params1 = {'gpu': 'RTX 4090', 'region': None}
        params2 = {'gpu': 'RTX 4090'}
        
        key1 = _cache_key('/providers', params1)
        key2 = _cache_key('/providers', params2)
        
        # Both should produce same key since None is filtered
        assert key1 == key2


# ============================================
# Provider Model Tests
# ============================================

@pytest.mark.django_db
class TestProviderModels:
    """Tests for provider models."""
    
    def test_create_provider(self):
        """Test creating a provider."""
        provider = Provider.objects.create(
            name='test_provider',
            display_name='Test Provider',
            api_base_url='https://api.test.com',
            status='active',
            reliability_score=0.95,
        )
        
        assert provider.id is not None
        assert provider.name == 'test_provider'
        assert provider.status == 'active'
    
    def test_create_gpu_offer(self, test_provider):
        """Test creating a GPU offer."""
        offer = GPUOffer.objects.create(
            provider=test_provider,
            external_id='test:rtx4090:us-east-1',
            name='RTX 4090 Instance',
            gpu_type='RTX 4090',
            gpu_memory_gb=24,
            cpu_cores=8,
            ram_gb=32,
            storage_gb=100,
            price_per_hour=Decimal('1.50'),
            currency='USD',
            region='us-east-1',
            availability_status='available',
        )
        
        assert offer.id is not None
        assert offer.gpu_type == 'RTX 4090'
        assert offer.price_per_hour == Decimal('1.50')
        assert offer.provider == test_provider
    
    def test_gpu_offer_compliance_tags(self, test_provider):
        """Test GPU offer with compliance tags."""
        offer = GPUOffer.objects.create(
            provider=test_provider,
            external_id='test:a100:eu-west-1',
            name='A100 Instance',
            gpu_type='A100',
            gpu_memory_gb=80,
            cpu_cores=16,
            ram_gb=64,
            storage_gb=200,
            price_per_hour=Decimal('3.50'),
            region='eu-west-1',
            compliance_tags=['soc2', 'gdpr', 'hipaa'],
        )
        
        assert 'soc2' in offer.compliance_tags
        assert 'gdpr' in offer.compliance_tags
        assert len(offer.compliance_tags) == 3


# ============================================
# Provider Service Tests
# ============================================

@pytest.mark.django_db(transaction=True)
class TestProviderServices:
    """Tests for provider service functions."""
    
    @pytest.mark.asyncio
    async def test_list_offers_no_filters(self, test_gpu_offers):
        """Test listing offers without filters."""
        result = await list_offers_from_db()
        
        assert result['total'] >= len(test_gpu_offers)
        assert len(result['items']) > 0
    
    @pytest.mark.asyncio
    async def test_list_offers_filter_by_gpu(self, test_gpu_offers):
        """Test filtering offers by GPU type."""
        result = await list_offers_from_db(gpu_term='RTX 4090')
        
        assert result['total'] >= 1
        for item in result['items']:
            assert 'RTX 4090' in item['gpu'] or 'RTX 4090' in item['name']
    
    @pytest.mark.asyncio
    async def test_list_offers_filter_by_region(self, test_gpu_offers):
        """Test filtering offers by region."""
        result = await list_offers_from_db(region='us-east-1')
        
        for item in result['items']:
            assert item['region'] == 'us-east-1'
    
    @pytest.mark.asyncio
    async def test_list_offers_filter_by_price(self, test_gpu_offers):
        """Test filtering offers by max price."""
        result = await list_offers_from_db(max_price=2.0)
        
        for item in result['items']:
            assert item['price_per_hour'] <= 2.0
    
    @pytest.mark.asyncio
    async def test_list_offers_filter_by_memory(self, test_gpu_offers):
        """Test filtering offers by GPU memory."""
        result = await list_offers_from_db(gpu_memory_min=24)
        
        for item in result['items']:
            assert item['memory_gb'] >= 24
    
    @pytest.mark.asyncio
    async def test_list_offers_pagination(self, test_gpu_offers):
        """Test offer pagination."""
        # Get first page
        page1 = await list_offers_from_db(page=1, per_page=2)
        
        # Get second page
        page2 = await list_offers_from_db(page=2, per_page=2)
        
        # Pages should have different items (if enough data)
        if page1['total'] > 2:
            page1_ids = {item['id'] for item in page1['items']}
            page2_ids = {item['id'] for item in page2['items']}
            assert page1_ids.isdisjoint(page2_ids)
    
    @pytest.mark.asyncio
    async def test_list_offers_combined_filters(self, test_gpu_offers):
        """Test combining multiple filters."""
        result = await list_offers_from_db(
            region='us-east-1',
            max_price=2.0,
            gpu_memory_min=10,
        )
        
        for item in result['items']:
            assert item['region'] == 'us-east-1'
            assert item['price_per_hour'] <= 2.0
            assert item['memory_gb'] >= 10


# ============================================
# Provider API Tests
# ============================================

@pytest.mark.django_db(transaction=True)
class TestProviderAPI:
    """Tests for provider API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_providers_endpoint(self, api_client, test_gpu_offers):
        """Test GET /providers endpoint."""
        response = await api_client.get('/providers/')
        
        assert response.status_code == 200
        data = response.json()
        assert 'total' in data
        assert 'items' in data
        assert isinstance(data['items'], list)
    
    @pytest.mark.asyncio
    async def test_list_providers_with_gpu_filter(self, api_client, test_gpu_offers):
        """Test GET /providers with GPU filter."""
        response = await api_client.get('/providers/?gpu=RTX')
        
        assert response.status_code == 200
        data = response.json()
        for item in data['items']:
            assert 'RTX' in item['gpu'].upper() or 'RTX' in item['name'].upper()
    
    @pytest.mark.asyncio
    async def test_list_providers_with_price_filter(self, api_client, test_gpu_offers):
        """Test GET /providers with price filter."""
        response = await api_client.get('/providers/?max_price=2.0')
        
        assert response.status_code == 200
        data = response.json()
        for item in data['items']:
            assert item['price_per_hour'] <= 2.0
    
    @pytest.mark.asyncio
    async def test_list_providers_pagination(self, api_client, test_gpu_offers):
        """Test GET /providers pagination."""
        response = await api_client.get('/providers/?page=1&per_page=2')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['items']) <= 2
    
    @pytest.mark.asyncio
    async def test_provider_health_endpoint(self, api_client):
        """Test GET /providers/health endpoint."""
        response = await api_client.get('/providers/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'providers' in data
        assert 'timestamp' in data
    
    @pytest.mark.asyncio
    async def test_integrations_endpoint_requires_auth(self, api_client):
        """Test GET /providers/config/integrations requires authentication."""
        response = await api_client.get('/providers/config/integrations')
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_integrations_endpoint_authenticated(self, api_client, auth_headers):
        """Test GET /providers/config/integrations with authentication."""
        response = await api_client.get(
            '/providers/config/integrations',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
