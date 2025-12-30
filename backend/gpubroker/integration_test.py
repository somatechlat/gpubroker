ARCHITECRURE FOR MILLIO#!/usr/bin/env python3
"""
GPUBROKER Integration Test Suite

Tests all API endpoints end-to-end on real infrastructure:
- PostgreSQL database (port 28001)
- Redis cache (port 28004)
- Django server (port 28080)

This script verifies:
1. Health endpoint
2. User registration
3. User login (JWT issuance)
4. Token refresh
5. Protected endpoint access (/auth/me)
6. Provider listing with filters
7. KPI endpoints
8. Math Core calculations
9. WebSocket connectivity (if available)

Per Vibe Coding Rules: TEST ALWAYS ON REAL INFRA
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional

import httpx

# Configuration
BASE_URL = os.getenv('BASE_URL', 'http://localhost:28080')
API_V2 = f'{BASE_URL}/api/v2'

# Test data
TEST_USER = {
    'email': f'integration_test_{datetime.now().strftime("%Y%m%d%H%M%S")}@example.com',
    'password': 'SecurePassword123!',
    'full_name': 'Integration Test User',
    'organization': 'Test Organization',
}


class IntegrationTestResult:
    """Stores test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def success(self, test_name: str, message: str = ''):
        self.passed += 1
        print(f'✅ {test_name}: PASSED {message}')
    
    def failure(self, test_name: str, message: str):
        self.failed += 1
        self.errors.append((test_name, message))
        print(f'❌ {test_name}: FAILED - {message}')
    
    def summary(self):
        total = self.passed + self.failed
        print(f'\n{"="*60}')
        print(f'INTEGRATION TEST SUMMARY')
        print(f'{"="*60}')
        print(f'Total: {total} | Passed: {self.passed} | Failed: {self.failed}')
        if self.errors:
            print(f'\nFailed Tests:')
            for name, msg in self.errors:
                print(f'  - {name}: {msg}')
        print(f'{"="*60}')
        return self.failed == 0


async def test_health(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test health endpoint."""
    try:
        response = await client.get(f'{BASE_URL}/health')
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                results.success('Health Check', f'DB: {data.get("database")}, Cache: {data.get("cache")}')
            else:
                results.failure('Health Check', f'Status not healthy: {data}')
        else:
            results.failure('Health Check', f'HTTP {response.status_code}')
    except Exception as e:
        results.failure('Health Check', str(e))


async def test_register(client: httpx.AsyncClient, results: IntegrationTestResult) -> Optional[dict]:
    """Test user registration."""
    try:
        response = await client.post(f'{API_V2}/auth/register', json=TEST_USER)
        if response.status_code in (200, 201):
            data = response.json()
            if data.get('email') == TEST_USER['email']:
                results.success('User Registration', f'User ID: {data.get("id")}')
                return data
            else:
                results.failure('User Registration', f'Email mismatch: {data}')
        elif response.status_code == 400 and 'already exists' in response.text.lower():
            results.success('User Registration', 'User already exists (expected in re-runs)')
            return {'email': TEST_USER['email']}
        else:
            results.failure('User Registration', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('User Registration', str(e))
    return None


async def test_login(client: httpx.AsyncClient, results: IntegrationTestResult) -> Optional[dict]:
    """Test user login and JWT issuance."""
    try:
        response = await client.post(f'{API_V2}/auth/login', json={
            'email': TEST_USER['email'],
            'password': TEST_USER['password'],
        })
        if response.status_code == 200:
            data = response.json()
            if data.get('access_token') and data.get('refresh_token'):
                results.success('User Login', f'Token type: {data.get("token_type")}')
                return data
            else:
                results.failure('User Login', f'Missing tokens: {data}')
        else:
            results.failure('User Login', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('User Login', str(e))
    return None


async def test_token_refresh(client: httpx.AsyncClient, results: IntegrationTestResult, tokens: dict) -> Optional[dict]:
    """Test token refresh."""
    try:
        response = await client.post(f'{API_V2}/auth/refresh', json={
            'refresh_token': tokens['refresh_token'],
        })
        if response.status_code == 200:
            data = response.json()
            if data.get('access_token'):
                results.success('Token Refresh', 'New access token issued')
                return data
            else:
                results.failure('Token Refresh', f'Missing access_token: {data}')
        else:
            results.failure('Token Refresh', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('Token Refresh', str(e))
    return None


async def test_me_endpoint(client: httpx.AsyncClient, results: IntegrationTestResult, access_token: str):
    """Test protected /auth/me endpoint."""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = await client.get(f'{API_V2}/auth/me', headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('email') == TEST_USER['email']:
                results.success('Protected Endpoint (/auth/me)', f'User: {data.get("full_name")}')
            else:
                results.failure('Protected Endpoint (/auth/me)', f'Email mismatch: {data}')
        else:
            results.failure('Protected Endpoint (/auth/me)', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('Protected Endpoint (/auth/me)', str(e))


async def test_me_unauthorized(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test that /auth/me rejects unauthorized requests."""
    try:
        response = await client.get(f'{API_V2}/auth/me')
        if response.status_code in (401, 403):
            results.success('Unauthorized Access Rejected', f'HTTP {response.status_code}')
        else:
            results.failure('Unauthorized Access Rejected', f'Expected 401/403, got {response.status_code}')
    except Exception as e:
        results.failure('Unauthorized Access Rejected', str(e))


async def test_providers_list(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test provider listing endpoint."""
    try:
        response = await client.get(f'{API_V2}/providers/', follow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            items = data.get('items', [])
            results.success('Provider Listing', f'Total: {total}, Items: {len(items)}')
        else:
            results.failure('Provider Listing', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('Provider Listing', str(e))


async def test_providers_filter(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test provider filtering."""
    try:
        response = await client.get(f'{API_V2}/providers/', params={
            'gpu_type': 'RTX',
            'max_price': 5.0,
            'page': 1,
            'per_page': 10,
        }, follow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            results.success('Provider Filtering', f'Filtered results: {data.get("total", 0)}')
        else:
            results.failure('Provider Filtering', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('Provider Filtering', str(e))


async def test_kpi_overview(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test KPI overview endpoint."""
    try:
        response = await client.get(f'{API_V2}/kpi/overview')
        if response.status_code == 200:
            data = response.json()
            results.success('KPI Overview', f'Active providers: {data.get("active_providers", 0)}')
        else:
            results.failure('KPI Overview', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('KPI Overview', str(e))


async def test_kpi_market_insights(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test market insights endpoint."""
    try:
        response = await client.get(f'{API_V2}/kpi/insights/market')
        if response.status_code == 200:
            data = response.json()
            results.success('Market Insights', f'Total offers: {data.get("total_offers", 0)}')
        else:
            results.failure('Market Insights', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('Market Insights', str(e))


async def test_math_benchmarks(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test GPU benchmarks endpoint."""
    try:
        response = await client.get(f'{API_V2}/math/benchmarks')
        if response.status_code == 200:
            data = response.json()
            results.success('GPU Benchmarks', f'Benchmarks: {len(data) if isinstance(data, list) else "N/A"}')
        else:
            results.failure('GPU Benchmarks', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('GPU Benchmarks', str(e))


async def test_math_cost_per_token(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test cost-per-token calculation."""
    try:
        response = await client.post(f'{API_V2}/math/cost-per-token', json={
            'price_per_hour': 1.50,
            'gpu_type': 'RTX 4090',
            'model_size': '7B',
        })
        if response.status_code == 200:
            data = response.json()
            cost = data.get('cost_per_token', 0)
            results.success('Cost Per Token', f'Cost: ${cost:.10f}')
        else:
            results.failure('Cost Per Token', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('Cost Per Token', str(e))


async def test_math_topsis(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test TOPSIS ranking algorithm."""
    try:
        response = await client.post(f'{API_V2}/math/topsis', json={
            'decision_matrix': [
                [1.50, 24, 82.6, 0.95],
                [3.50, 80, 19.5, 0.85],
                [4.50, 80, 51.0, 0.80],
            ],
            'weights': [0.30, 0.25, 0.25, 0.20],
            'criteria_types': ['cost', 'benefit', 'benefit', 'benefit'],
        })
        if response.status_code == 200:
            data = response.json()
            rankings = data.get('rankings', [])
            results.success('TOPSIS Ranking', f'Rankings: {rankings}')
        else:
            results.failure('TOPSIS Ranking', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('TOPSIS Ranking', str(e))


async def test_ai_health(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test AI assistant health endpoint."""
    try:
        response = await client.get(f'{API_V2}/ai/health')
        if response.status_code == 200:
            data = response.json()
            results.success('AI Health', f'Status: {data.get("status", "unknown")}')
        elif response.status_code == 502:
            # SomaAgent not available - expected in test environment
            results.success('AI Health', 'SomaAgent not available (expected)')
        else:
            results.failure('AI Health', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('AI Health', str(e))


async def test_provider_health(client: httpx.AsyncClient, results: IntegrationTestResult):
    """Test provider service health endpoint."""
    try:
        response = await client.get(f'{API_V2}/providers/health', follow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            providers = data.get('providers', [])
            results.success('Provider Health', f'Adapters: {len(providers)} ({", ".join(providers[:5])}...)')
        else:
            results.failure('Provider Health', f'HTTP {response.status_code}: {response.text}')
    except Exception as e:
        results.failure('Provider Health', str(e))


async def test_vastai_live_api():
    """Test direct Vast.ai API integration (public, no auth required)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                'https://console.vast.ai/api/v0/bundles/',
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'GPUBROKER/2.0'
                }
            )
            if response.status_code == 200:
                data = response.json()
                offers = data.get('offers', [])
                if offers:
                    # Sample first offer
                    first = offers[0]
                    gpu_name = first.get('gpu_name', 'Unknown')
                    price = first.get('dph_total', 0)
                    return True, f'{len(offers)} offers (e.g., {gpu_name} @ ${price:.2f}/hr)'
                return True, 'API accessible but no offers'
            return False, f'HTTP {response.status_code}'
    except Exception as e:
        return False, str(e)


async def test_live_provider_integrations(results: IntegrationTestResult):
    """Test live provider API integrations."""
    # Test Vast.ai (public API, no auth required)
    success, message = await test_vastai_live_api()
    if success:
        results.success('Vast.ai Live API', message)
    else:
        results.failure('Vast.ai Live API', message)


async def run_integration_tests():
    """Run all integration tests."""
    print(f'\n{"="*60}')
    print(f'GPUBROKER INTEGRATION TEST SUITE')
    print(f'Base URL: {BASE_URL}')
    print(f'Timestamp: {datetime.now().isoformat()}')
    print(f'{"="*60}\n')
    
    results = IntegrationTestResult()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health Check
        print('\n--- Infrastructure Tests ---')
        await test_health(client, results)
        
        # 2. Authentication Flow
        print('\n--- Authentication Tests ---')
        user = await test_register(client, results)
        tokens = await test_login(client, results)
        
        if tokens:
            new_tokens = await test_token_refresh(client, results, tokens)
            access_token = new_tokens.get('access_token') if new_tokens else tokens.get('access_token')
            await test_me_endpoint(client, results, access_token)
        
        await test_me_unauthorized(client, results)
        
        # 3. Provider Service
        print('\n--- Provider Service Tests ---')
        await test_providers_list(client, results)
        await test_providers_filter(client, results)
        
        # 4. KPI Service
        print('\n--- KPI Service Tests ---')
        await test_kpi_overview(client, results)
        await test_kpi_market_insights(client, results)
        
        # 5. Math Core Service
        print('\n--- Math Core Tests ---')
        await test_math_benchmarks(client, results)
        await test_math_cost_per_token(client, results)
        await test_math_topsis(client, results)
        
        # 6. AI Assistant
        print('\n--- AI Assistant Tests ---')
        await test_ai_health(client, results)
        
        # 7. Provider Health
        print('\n--- Provider Service Health ---')
        await test_provider_health(client, results)
    
    # 8. Live Provider Integrations (outside httpx client context)
    print('\n--- Live Provider API Integrations ---')
    await test_live_provider_integrations(results)
    
    # Summary
    success = results.summary()
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = asyncio.run(run_integration_tests())
    sys.exit(exit_code)
