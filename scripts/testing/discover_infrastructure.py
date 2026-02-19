#!/usr/bin/env python3
"""
DISCOVER WHAT'S ACTUALLY RUNNING ON THE INFRASTRUCTURE
Find and test the actual services that are up.
"""

import asyncio
import sys
import httpx
from datetime import datetime


async def discover_running_services():
    """Discover what's actually running on the active ports."""
    print("🔍 DISCOVERING ACTUAL RUNNING SERVICES")
    print("=" * 60)

    # Based on docker ps output, these services are running on these ports
    test_ports = [
        5000,  # agent-zero-app
        63900,  # soma-stack main service
        63996,  # soma-stack
        63690,  # lago-front
        63691,  # lago-api
        63692,  # lago-db
        63693,  # lago-redis
        63694,  # lago-pdf
        65006,  # shared_keycloak
        65004,  # shared_postgres
        65005,  # shared_redis
        65003,  # shared_vault
    ]

    services_found = []

    for port in test_ports:
        try:
            print(f"🔍 Scanning port {port}...", end=" ")

            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                # Test root endpoint
                response = await client.get(f"http://localhost:{port}/")

                print(f"✅ {response.status_code}")

                # Parse response to identify service
                content = response.text[:200]

                # Try to identify the service
                service_info = identify_service(port, response, content)
                services_found.append(service_info)

        except httpx.ConnectError:
            print("❌ Connection refused")
        except httpx.TimeoutException:
            print("❌ Timeout")
        except Exception as e:
            print(f"❌ {str(e)[:50]}")

    return services_found


def identify_service(port, response, content):
    """Identify what service is running based on response."""
    status = response.status_code

    # Check for known service indicators
    if status == 200:
        if "soma" in content.lower() or "saas" in content.lower():
            return {
                "port": port,
                "service": "Soma Stack",
                "status": "working",
                "url": f"http://localhost:{port}",
            }
        elif "keycloak" in content.lower() or "welcome" in content.lower():
            return {
                "port": port,
                "service": "Keycloak",
                "status": "working",
                "url": f"http://localhost:{port}",
            }
        elif "lago" in content.lower():
            return {
                "port": port,
                "service": "Lago",
                "status": "working",
                "url": f"http://localhost:{port}",
            }
        elif "agent" in content.lower() or "api" in content.lower():
            return {
                "port": port,
                "service": "Agent Zero",
                "status": "working",
                "url": f"http://localhost:{port}",
            }
        else:
            return {
                "port": port,
                "service": "Unknown Web Service",
                "status": "working",
                "url": f"http://localhost:{port}",
            }
    elif status == 404:
        return {
            "port": port,
            "service": "Web Service (404)",
            "status": "partial",
            "url": f"http://localhost:{port}",
        }
    elif status == 401 or status == 403:
        return {
            "port": port,
            "service": "Secured Service",
            "status": "working",
            "url": f"http://localhost:{port}",
        }
    else:
        return {
            "port": port,
            "service": f"HTTP {status}",
            "status": "unknown",
            "url": f"http://localhost:{port}",
        }


async def test_soma_stack():
    """Test the Soma stack that appears to be running."""
    print("\n🧪 TESTING SOMA STACK INTEGRATION")
    print("=" * 50)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test main endpoint
            response = await client.get("http://localhost:63900/")

            if response.status_code == 200:
                print("✅ Soma Stack responding")
                content = response.text

                # Look for API endpoints
                if "api" in content.lower():
                    print("🔍 Looking for API endpoints...")

                    # Try common API paths
                    api_paths = [
                        "/api/v1/",
                        "/api/v2/",
                        "/api/",
                        "/providers/",
                        "/health",
                    ]

                    for path in api_paths:
                        try:
                            api_response = await client.get(
                                f"http://localhost:63900{path}"
                            )
                            if api_response.status_code == 200:
                                print(f"   ✅ Found API: http://localhost:63900{path}")
                            elif api_response.status_code == 404:
                                print(
                                    f"   📁 Path not found: http://localhost:63900{path}"
                                )
                        except:
                            continue

            else:
                print(f"❌ Soma Stack returned {response.status_code}")

    except Exception as e:
        print(f"❌ Soma Stack test failed: {str(e)}")


async def test_database_direct():
    """Test databases directly."""
    print("\n💾 TESTING DATABASES DIRECTLY")
    print("=" * 40)

    databases = []

    # Test Redis connections
    redis_ports = [63979, 65005]
    for port in redis_ports:
        try:
            import redis.asyncio as redis

            client = redis.Redis(host="localhost", port=port, decode_responses=True)
            result = await client.ping()
            if result:
                databases.append({"type": "Redis", "port": port, "status": "connected"})
                print(f"✅ Redis connected on port {port}")
        except Exception as e:
            print(f"❌ Redis failed on port {port}: {str(e)[:30]}")

    # Test PostgreSQL
    postgres_ports = [63932, 65004]
    for port in postgres_ports:
        try:
            import asyncpg

            conn = await asyncpg.connect(
                host="localhost",
                port=port,
                user="postgres",
                password="",
                database="postgres",
                timeout=3.0,
            )
            await conn.close()
            databases.append(
                {"type": "PostgreSQL", "port": port, "status": "connected"}
            )
            print(f"✅ PostgreSQL connected on port {port}")
        except Exception as e:
            print(f"❌ PostgreSQL failed on port {port}: {str(e)[:30]}")

    return databases


async def main():
    """Main discovery function."""
    print("🔍 DISCOVERING ACTUAL INFRASTRUCTURE SERVICES")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Discover all services
    services = await discover_running_services()

    # Test specific stacks
    await test_soma_stack()
    databases = await test_database_direct()

    # Analyze findings
    print("\n" + "=" * 60)
    print("🏆 INFRASTRUCTURE DISCOVERY RESULTS")
    print("=" * 60)

    web_services = [s for s in services if s["status"] in ["working", "partial"]]
    db_services = [d for d in databases if d["status"] == "connected"]

    print(f"🌐 Web Services Found: {len(web_services)}")
    for service in web_services:
        print(f"   📦 {service['service']:20} - {service['url']} ({service['status']})")

    print(f"\n💾 Databases Connected: {len(db_services)}")
    for db in db_services:
        print(f"   🗄️  {db['type']:12} - Port {db['port']}")

    # Look for GPUBroker opportunities
    print(f"\n🎯 GPUBROKER INTEGRATION OPPORTUNITIES:")

    if any(s["service"] == "Soma Stack" for s in services):
        print("✅ Soma Stack is running - potential integration point")
        print("📋 Could extend Soma with GPU marketplace API")

    if any(s["service"] == "Agent Zero" for s in services):
        print("✅ Agent Zero is running - direct integration available")
        print("📋 Connect GPUBroker providers to Agent Zero")

    if len(db_services) >= 2:
        print("✅ Multiple databases available - ready for GPUBroker deployment")
        print("📋 Can deploy GPUBroker alongside existing services")

    # Next steps
    print(f"\n🚀 RECOMMENDED NEXT STEPS:")
    if len(web_services) >= 3:
        print("1. ✅ Infrastructure is healthy - deploy GPUBroker")
        print("2. 📋 Deploy with: cd infrastructure/docker && docker compose up -d")
        print("3. 🔗 Integrate with existing services via APIs")
    else:
        print("1. ⚠️  Some services missing - check deployment")
        print("2. 🔧 Fix any configuration issues")
        print("3. 🚀 Then deploy GPUBroker")

    return 0 if web_services else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
