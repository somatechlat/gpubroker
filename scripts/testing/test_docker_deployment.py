#!/usr/bin/env python3
"""
DOCKER DEPLOYMENT TEST FOR GPUBROKER
Test if the system can be deployed and accessed via Docker.
"""

import asyncio
import sys
import os
import httpx
from datetime import datetime


async def test_docker_deployment():
    """Test if GPUBroker is accessible via Docker."""
    print("🐳 DOCKER DEPLOYMENT TEST FOR GPUBROKER")
    print("=" * 60)

    # Test different ports where GPUBroker might be running
    test_ports = [
        80,  # Main nginx port
        28080,  # Django direct port
        28030,  # Frontend port
        10355,  # Alternative port (mentioned in docs)
    ]

    services_found = []

    for port in test_ports:
        print(f"🔍 Testing port {port}...", end=" ")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Test health endpoint
                response = await client.get(f"http://localhost:{port}/health")

                if response.status_code == 200:
                    print("✅ HEALTH CHECK PASSED")
                    services_found.append(
                        f"Port {port} - {response.json() if response.text else 'OK'}"
                    )
                else:
                    print(f"❌ HTTP {response.status_code}")

        except httpx.ConnectError:
            print("❌ Connection refused")
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")

    # Test provider API if main service is found
    if any(
        80 in service
        for service in services_found
        for service in service
        if 80 in service
    ):
        print(f"\n🌐 Testing GPUBroker Provider API on port 80...")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost/api/v2/providers/health")

                if response.status_code == 200:
                    print("✅ Provider API Health Check Passed")
                    data = response.json()
                    print(f"   📋 Providers available: {data.get('providers', [])}")
                    services_found.append("Provider API working")
                else:
                    print(f"❌ Provider API returned {response.status_code}")

        except Exception as e:
            print(f"❌ Provider API Error: {str(e)}")

    return services_found


async def test_provider_api_direct():
    """Test provider API directly if Django is running."""
    print("\n🔍 TESTING DJANGO PROVIDER API DIRECT")
    print("=" * 50)

    django_ports = [28080, 10355]

    for port in django_ports:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                print(f"🧪 Testing Django API on port {port}...")

                # Test provider health endpoint
                response = await client.get(
                    f"http://localhost:{port}/api/v2/providers/health"
                )

                if response.status_code == 200:
                    print("✅ Django Provider API working!")
                    data = response.json()
                    print(
                        f"   📋 Available providers: {len(data.get('providers', []))}"
                    )
                    print(
                        f"   🌐 API endpoint: http://localhost:{port}/api/v2/providers/"
                    )

                    # Test actual provider data fetch
                    print("\n📊 Testing provider data fetch...")
                    data_response = await client.get(
                        f"http://localhost:{port}/api/v2/providers/"
                    )

                    if data_response.status_code == 200:
                        data = data_response.json()
                        total_offers = data.get("total", 0)
                        print(f"   ✅ Successfully fetched {total_offers} GPU offers!")

                        if total_offers > 0:
                            print("   🎉 GPUBroker is FULLY FUNCTIONAL in Docker!")
                            return True
                    else:
                        print(
                            f"   ❌ Provider fetch failed: {data_response.status_code}"
                        )
                else:
                    print(f"❌ Django API returned {response.status_code}")

        except Exception as e:
            print(f"❌ Django API Error on port {port}: {str(e)[:50]}")

    return False


async def check_existing_containers():
    """Check what GPUBroker containers are running."""
    print("\n🐳 CHECKING RUNNING CONTAINERS")
    print("=" * 40)

    try:
        result = os.popen(
            "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
        ).read()
        containers = result.strip().split("\n")[1:]  # Skip header

        gpubroker_containers = [
            c for c in containers if "gpubroker" in c.lower() or "docker-" in c.lower()
        ]

        if gpubroker_containers:
            print("✅ Found potential GPUBroker containers:")
            for container in gpubroker_containers:
                print(f"   📦 {container}")
            return True
        else:
            print("❌ No GPUBroker containers found")
            return False

    except Exception as e:
        print(f"❌ Error checking containers: {str(e)}")
        return False


async def main():
    """Main test function."""
    print("🚀 GPUBROKER DOCKER DEPLOYMENT VERIFICATION")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check containers
    await check_existing_containers()

    # Test deployment
    services = await test_docker_deployment()

    # Test API directly
    api_working = await test_provider_api_direct()

    # Final verdict
    print("\n" + "=" * 60)
    print("🏆 DOCKER DEPLOYMENT VERDICT")
    print("=" * 60)

    if api_working:
        print("🎉 SUCCESS! GPUBroker is FULLY DEPLOYED and WORKING in Docker!")
        print("✅ Provider API is serving live GPU marketplace data")
        print("🚀 Ready for production use!")
        return 0
    elif services:
        print("⚠️  PARTIAL SUCCESS: Services running but API not fully accessible")
        print(f"📋 Found services: {', '.join(services)}")
        return 1
    else:
        print("❌ DEPLOYMENT NEEDED: GPUBroker not found running in Docker")
        print("\n📋 TO DEPLOY GPUBroker:")
        print("1. cd infrastructure/docker")
        print("2. docker compose up -d")
        print("3. Access at http://localhost")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
