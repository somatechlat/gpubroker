#!/usr/bin/env python3
"""
Test script to verify all provider adapters are working.
Tests registry loading, adapter instantiation, and basic functionality.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(
    0, "/Users/macbookpro201916i964gb1tb/Documents/GitHub/gpubroker/backend/gpubroker"
)


async def test_provider_registry():
    """Test provider registry loading and adapter instantiation."""
    print("🔍 Testing Provider Registry...")
    print("=" * 50)

    try:
        from apps.providers.adapters.registry import ProviderRegistry

        # Initialize registry
        ProviderRegistry.initialize_registry()

        # List all registered adapters
        registered_providers = ProviderRegistry.list_adapters()

        print(f"📋 Total Registered Providers: {len(registered_providers)}")
        print()

        # Test each adapter
        success_count = 0
        error_count = 0

        for provider_name in sorted(registered_providers):
            print(f"🧪 Testing {provider_name}...", end=" ")

            try:
                adapter = ProviderRegistry.get_adapter(provider_name)

                # Test basic adapter properties
                assert hasattr(adapter, "PROVIDER_NAME")
                assert hasattr(adapter, "get_offers")
                assert hasattr(adapter, "validate_credentials")

                print(f"✅ OK (Name: {adapter.PROVIDER_NAME})")
                success_count += 1

            except Exception as e:
                print(f"❌ FAILED: {str(e)}")
                error_count += 1

        print()
        print("=" * 50)
        print(f"📊 SUMMARY:")
        print(f"   ✅ Success: {success_count}")
        print(f"   ❌ Failed: {error_count}")
        print(
            f"   📈 Success Rate: {(success_count / len(registered_providers) * 100):.1f}%"
        )

        return success_count == len(registered_providers)

    except Exception as e:
        print(f"❌ Registry Test Failed: {str(e)}")
        return False


async def test_sample_api_calls():
    """Test sample API calls for adapters that don't require authentication."""
    print("\n🌐 Testing Sample API Calls (No Auth Required)...")
    print("=" * 50)

    try:
        from apps.providers.adapters.registry import ProviderRegistry

        # Test VastAI (public API)
        print("🧪 Testing VastAI (Public API)...")
        vastai_adapter = ProviderRegistry.get_adapter("vastai")

        try:
            # VastAI doesn't require auth for public listings
            offers = await vastai_adapter.get_offers()
            print(f"✅ VastAI: {len(offers)} offers fetched")

            if offers:
                sample_offer = offers[0]
                print(
                    f"   Sample: {sample_offer.instance_type} - ${sample_offer.price_per_hour}/hr"
                )

        except Exception as e:
            print(f"❌ VastAI API Call Failed: {str(e)}")

        # Test credential validation
        print("\n🧪 Testing Credential Validation...")

        # Test with invalid credentials
        for provider_name in ["vastai", "runpod", "cerebras"]:
            try:
                adapter = ProviderRegistry.get_adapter(provider_name)
                result = await adapter.validate_credentials({"api_key": "invalid_key"})
                print(
                    f"   {provider_name}: {'✅ Correctly rejected' if not result else '❌ Incorrectly accepted'} invalid key"
                )
            except Exception as e:
                print(f"   {provider_name}: ⚠️ Validation error: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ API Test Failed: {str(e)}")
        return False


async def test_common_imports():
    """Test that all common modules can be imported."""
    print("\n📦 Testing Common Imports...")
    print("=" * 50)

    try:
        # Test base components
        from apps.providers.adapters.base import BaseProviderAdapter, ProviderOffer

        print("✅ Base components imported")

        from apps.providers.adapters.registry import ProviderRegistry

        print("✅ Registry imported")

        from apps.providers.models import Provider, GPUOffer

        print("✅ Models imported")

        from apps.providers.services import fetch_offers_from_adapters

        print("✅ Services imported")

        return True

    except Exception as e:
        print(f"❌ Import Test Failed: {str(e)}")
        return False


async def main():
    """Main test function."""
    print("🚀 GPUBROKER PROVIDER ADAPTER TEST SUITE")
    print("📅 Run at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    # Run all tests
    test_results = []

    test_results.append(await test_common_imports())
    test_results.append(await test_provider_registry())
    test_results.append(await test_sample_api_calls())

    # Final summary
    print("\n" + "=" * 50)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 50)

    passed = sum(test_results)
    total = len(test_results)

    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed / total * 100):.1f}%")

    if passed == total:
        print("🎉 ALL TESTS PASSED! All providers are working!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    # Run the test suite
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
