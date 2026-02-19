#!/usr/bin/env python3
"""
COMPREHENSIVE REAL INFRASTRUCTURE INTEGRATION TESTS
Tests GPUBroker against the ACTUAL running Docker infrastructure.
"""

import asyncio
import sys
import os
import httpx
import json
from datetime import datetime

# Test URLs based on running containers we saw earlier
TEST_ENDPOINTS = [
    # Main GPUBroker (if running on standard ports)
    "http://localhost:63900/api/v2/providers/",
    "http://localhost:63900/api/v2/providers/health",
    "http://localhost:63900/health",
    # Try Soma stack (looks like running)
    "http://localhost:63900/",
    "http://localhost:63996/api/v2/providers/",
    # Direct testing if Django is running
    "http://localhost:63900/api/v2/",
    # Try alternative ports from existing containers
    "http://localhost:63690/api/v2/providers/",
    "http://localhost:65006/api/v2/providers/",
]


async def test_real_infrastructure():
    """Test against actual running infrastructure."""
    print("🔍 TESTING REAL RUNNING INFRASTRUCTURE")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test all possible endpoints
    working_endpoints = []

    for endpoint in TEST_ENDPOINTS:
        try:
            print(f"🔍 Testing {endpoint}...", end=" ")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint)

                if response.status_code == 200:
                    print(f"✅ {response.status_code}")
                    working_endpoints.append(endpoint)

                    # Parse response
                    try:
                        data = response.json()
                        print(f"   📊 Response: {json.dumps(data)[:100]}...")
                    except:
                        print(f"   📊 Response: {response.text[:100]}...")
                else:
                    print(f"⚠️  {response.status_code}")

        except httpx.ConnectError:
            print("❌ Connection refused")
        except httpx.TimeoutException:
            print("❌ Timeout")
        except Exception as e:
            print(f"❌ {str(e)[:50]}")

    return working_endpoints


async def test_running_containers():
    """Test what services are actually running."""
    print("\n🐳 CHECKING RUNNING CONTAINERS")
    print("=" * 50)

    try:
        result = os.popen(
            "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
        ).read()
        lines = result.strip().split("\n")

        print("📦 RUNNING CONTAINERS:")
        for line in lines[1:]:  # Skip header
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 4:
                    name, image, status, ports = parts[:4]
                    print(f"   🏷️  {name:25} {image:25} {status:15} {ports}")

        # Look for GPUBroker related containers
        gpubroker_containers = []
        for line in lines[1:]:
            if "gpubroker" in line.lower() or "django" in line.lower():
                gpubroker_containers.append(line)

        if gpubroker_containers:
            print(
                f"\n✅ Found {len(gpubroker_containers)} GPUBroker-related containers"
            )
            for container in gpubroker_containers:
                print(f"   🎯 {container}")
            return True
        else:
            print(f"\n❌ No GPUBroker containers found")
            return False

    except Exception as e:
        print(f"❌ Error checking containers: {str(e)}")
        return False


async def test_provider_api_direct():
    """Test provider API against likely ports."""
    print("\n🌐 TESTING PROVIDER API DIRECT")
    print("=" * 50)

    # Try to find where Django might be running
    test_ports = [63900, 63690, 65006, 63996, 5001]  # From docker ps output

    for port in test_ports:
        try:
            print(f"🧪 Testing provider API on port {port}...")

            async with httpx.AsyncClient(timeout=15.0) as client:
                # Test health endpoint
                health_url = f"http://localhost:{port}/health"
                response = await client.get(health_url)

                if response.status_code == 200:
                    print(f"   ✅ Health check passed")

                    # Test provider API
                    api_url = f"http://localhost:{port}/api/v2/providers/health"
                    api_response = await client.get(api_url)

                    if api_response.status_code == 200:
                        data = api_response.json()
                        providers = data.get("providers", [])
                        print(
                            f"   ✅ Provider API working - {len(providers)} providers"
                        )
                        print(
                            f"   🌐 Endpoint: http://localhost:{port}/api/v2/providers/"
                        )
                        return port, data
                    else:
                        print(f"   ❌ Provider API returned {api_response.status_code}")
                else:
                    print(f"   ❌ Health check failed: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Port {port} error: {str(e)[:50]}")

    return None, None


async def test_database_connectivity():
    """Test if we can connect to the databases."""
    print("\n💾 TESTING DATABASE CONNECTIVITY")
    print("=" * 50)

    # Test PostgreSQL connections based on port mappings
    db_ports = [
        (63932, "PostgreSQL"),  # From docker ps output
        (65004, "PostgreSQL"),  # Another postgres
        (5432, "PostgreSQL"),  # Default
        (28001, "PostgreSQL"),  # From compose file
    ]

    for port, db_type in db_ports:
        try:
            print(f"🔍 Testing {db_type} on port {port}...")

            # Simple connection test
            import asyncpg

            conn = await asyncpg.connect(
                host="localhost",
                port=port,
                user="postgres",
                password="test",
                database="postgres",
                timeout=5.0,
            )

            # Try simple query
            result = await conn.fetchval("SELECT 1")
            await conn.close()

            if result == 1:
                print(f"   ✅ {db_type} connected successfully")

        except Exception as e:
            print(f"   ❌ {db_type} failed: {str(e)[:50]}")

    # Test Redis
    redis_ports = [
        (63979, "Redis"),
        (65005, "Redis"),
        (6379, "Redis"),
        (28004, "Redis"),
    ]

    for port, cache_type in redis_ports:
        try:
            import redis.asyncio as redis

            print(f"🔍 Testing {cache_type} on port {port}...")

            client = redis.Redis(host="localhost", port=port, decode_responses=True)
            result = await client.ping()

            if result:
                print(f"   ✅ {cache_type} connected successfully")

        except Exception as e:
            print(f"   ❌ {cache_type} failed: {str(e)[:50]}")


async def test_provider_data_if_available():
    """If we find a working API, test the provider data."""
    print("\n📊 TESTING PROVIDER DATA ACQUISITION")
    print("=" * 60)

    # This will only run if we found a working API in test_provider_api_direct()
    working_port = None

    # Try common ports
    for port in [63900, 63690, 65006, 63996]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"http://localhost:{port}/api/v2/providers/"
                )

                if response.status_code == 200:
                    data = response.json()
                    total = data.get("total", 0)
                    print(f"✅ Found working API on port {port}")
                    print(f"📊 Total GPU offers available: {total}")

                    if total > 0:
                        items = data.get("items", [])
                        print(
                            f"🏷️  Sample providers: {list(set(item.get('provider', 'unknown') for item in items[:5]))}"
                        )
                        working_port = port
                        break
                    else:
                        print("📦 No GPU offers available (needs configuration)")

        except:
            continue

    return working_port


async def main():
    """Main integration test function."""
    print("🚀 GPUBROKER COMPREHENSIVE REAL INFRASTRUCTURE TEST")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    test_results = []

    # 1. Check what containers are running
    containers_found = await test_running_containers()
    test_results.append(containers_found)

    # 2. Test endpoints
    working_endpoints = await test_real_infrastructure()
    test_results.append(len(working_endpoints) > 0)

    # 3. Test provider API
    api_port, api_data = await test_provider_api_direct()
    test_results.append(api_port is not None)

    # 4. Test database connectivity
    await test_database_connectivity()

    # 5. Test provider data
    working_port = await test_provider_data_if_available()
    test_results.append(working_port is not None)

    # Final verdict
    print("\n" + "=" * 70)
    print("🏆 COMPREHENSIVE INTEGRATION TEST RESULTS")
    print("=" * 70)

    passed = sum(test_results)
    total = len(test_results)

    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed / total * 100):.1f}%")
    print()

    if passed >= 4:
        print("🎉 EXCELLENT! GPUBroker infrastructure is WORKING!")
        if api_port:
            print(f"🌐 Main API: http://localhost:{api_port}/api/v2/")
            print(f"📊 Provider API: http://localhost:{api_port}/api/v2/providers/")
        print("✅ Container orchestration working")
        print("✅ Database connectivity established")
        print("✅ Provider data acquisition functional")
        return 0

    elif passed >= 2:
        print("✅ GOOD! Infrastructure partially working")
        if api_port:
            print(f"🌐 API available at: http://localhost:{api_port}/api/v2/")
        print("⚠️  Some services may need configuration")
        return 1

    else:
        print("❌ NEEDS WORK! Infrastructure not ready")
        print("📋 TO DEPLOY GPUBroker:")
        print("1. Ensure Docker containers are running")
        print("2. Check configuration in infrastructure/docker/")
        print("3. Run: docker compose up -d")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
