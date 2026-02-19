#!/usr/bin/env python3
"""
REAL API TEST - Verify we're actually pulling live data from providers.
Tests with actual API calls to validate data acquisition.
"""

import asyncio
import sys
import os
from datetime import datetime
import json

# Add to path
sys.path.insert(
    0, "/Users/macbookpro201916i964gb1tb/Documents/GitHub/gpubroker/backend/gpubroker"
)


async def test_real_api_calls():
    """Test real API calls to verify we're getting live data."""
    print("🌐 TESTING REAL API CALLS - LIVE DATA VERIFICATION")
    print("=" * 70)

    try:
        from apps.providers.adapters.registry import ProviderRegistry
        from apps.providers.adapters.base import ProviderOffer

        # Initialize registry
        ProviderRegistry.initialize_registry()

        all_providers = ProviderRegistry.list_adapters()
        live_data_providers = 0
        mock_data_providers = 0
        error_providers = 0

        print(f"📋 Testing {len(all_providers)} providers for LIVE DATA...")
        print()

        for provider_name in sorted(all_providers):
            print(f"🧪 {provider_name:15} ", end="")

            try:
                adapter = ProviderRegistry.get_adapter(provider_name)

                # Test with no auth first
                offers = await adapter.get_offers(auth_token=None)

                if offers:
                    # Check if this looks like real data vs mock data
                    is_real_data = analyze_data_realism(provider_name, offers)

                    if is_real_data:
                        print(f"✅ LIVE DATA ({len(offers)} offers)")
                        live_data_providers += 1

                        # Show sample details
                        sample = offers[0]
                        print(f"     🌐 API: {adapter.BASE_URL}")
                        print(
                            f"     📊 Sample: {sample.instance_type[:30]:30} - ${sample.price_per_hour:.4f}/hr"
                        )
                        print(f"     🏷️  Tags: {sample.compliance_tags}")
                    else:
                        print(f"📦 MOCK DATA ({len(offers)} offers)")
                        mock_data_providers += 1
                else:
                    print("📦 NO DATA (mock/needs auth)")
                    mock_data_providers += 1

            except Exception as e:
                print(f"❌ ERROR: {str(e)[:50]}")
                error_providers += 1

        print("\n" + "=" * 70)
        print("📊 LIVE DATA ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"   🌐 Real Live Data Providers: {live_data_providers}")
        print(f"   📦 Mock/Demo Data Providers: {mock_data_providers}")
        print(f"   ❌ Error Providers: {error_providers}")
        print(
            f"   📈 Live Data Rate: {(live_data_providers / len(all_providers) * 100):.1f}%"
        )

        return live_data_providers, mock_data_providers, error_providers

    except Exception as e:
        print(f"❌ Real API Test Failed: {str(e)}")
        return 0, 0, 0


def analyze_data_realism(provider_name, offers):
    """Analyze if offers look like real API data vs mock data."""
    if not offers:
        return False

    sample = offers[0]

    # Check for signs of real data
    realism_indicators = 0

    # 1. Price variation (real data has varied pricing)
    prices = [offer.price_per_hour for offer in offers]
    if len(set([round(p, 2) for p in prices])) > 2:
        realism_indicators += 1

    # 2. Realistic instance names
    if any(
        pattern in sample.instance_type.lower()
        for pattern in ["gpu", "a100", "h100", "rtx", "v100", "t4", "p100", "l4"]
    ):
        realism_indicators += 1

    # 3. Non-zero prices
    if sample.price_per_hour > 0:
        realism_indicators += 1

    # 4. Real compliance tags
    real_tags = ["aws", "azure", "google", "nvidia", "cerebras", "groq", "replicate"]
    if any(tag in sample.compliance_tags for tag in real_tags):
        realism_indicators += 1

    # 5. Meaningful region info
    if sample.region and sample.region not in ["global", "unknown", ""]:
        realism_indicators += 1

    # Check for mock data indicators
    mock_indicators = 0

    # Constant pricing (sign of mock data)
    if len(set([round(p, 2) for p in prices])) == 1:
        mock_indicators += 2

    # Generic names
    if sample.instance_type.startswith("Mock") or "Demo" in sample.instance_type:
        mock_indicators += 2

    # All providers have same tags
    if len(set(sample.compliance_tags)) == 1:
        mock_indicators += 1

    # Return True if realism indicators outweigh mock indicators
    return realism_indicators >= 3 and mock_indicators <= 2


async def test_vastai_public_api():
    """Test VastAI public API specifically - this should work without auth."""
    print("\n🎯 TESTING VASTAI PUBLIC API (SHOULD WORK)")
    print("=" * 50)

    try:
        from apps.providers.adapters.registry import ProviderRegistry

        vastai = ProviderRegistry.get_adapter("vastai")

        print("🔍 Fetching from VastAI public API...")
        offers = await vastai.get_offers()

        if offers:
            print(f"✅ SUCCESS: {len(offers)} offers from VastAI")

            # Analyze the data
            prices = [offer.price_per_hour for offer in offers]
            print(f"💰 Price range: ${min(prices):.4f} - ${max(prices):.4f}/hr")
            print(f"📈 Unique prices: {len(set([round(p, 3) for p in prices]))}")

            # Show diverse samples
            gpu_types = set(offer.instance_type for offer in offers[:5])
            print(f"🖥️  GPU types: {list(gpu_types)[:5]}")

            # Check for real GPU names
            real_gpus = sum(
                1
                for offer in offers[:10]
                if any(
                    gpu in offer.instance_type.lower()
                    for gpu in ["rtx", "a100", "h100", "v100", "t4"]
                )
            )
            print(f"🎮 Real GPU models: {real_gpus}/10")

            return True
        else:
            print("❌ FAILED: No offers from VastAI")
            return False

    except Exception as e:
        print(f"❌ VastAI Test Failed: {str(e)}")
        return False


async def test_credential_validation():
    """Test credential validation with real API calls."""
    print("\n🔐 TESTING CREDENTIAL VALIDATION")
    print("=" * 50)

    try:
        from apps.providers.adapters.registry import ProviderRegistry

        # Test RunPod credential validation (should fail gracefully)
        runpod = ProviderRegistry.get_adapter("runpod")

        print("🧪 RunPod with invalid credentials...")
        is_valid = await runpod.validate_credentials(
            {"api_key": "invalid_key_that_should_fail"}
        )

        if not is_valid:
            print("✅ Correctly rejected invalid credentials")
            return True
        else:
            print("❌ Incorrectly accepted invalid credentials")
            return False

    except Exception as e:
        print(f"❌ Credential Test Failed: {str(e)}")
        return False


async def main():
    """Main test function."""
    print("🚀 GPUBROKER REAL API DATA VERIFICATION")
    print(f"📅 Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    test_results = []

    # Test real API calls
    live, mock, errors = await test_real_api_calls()
    test_results.append(live > 0)

    # Test VastAI public API specifically
    test_results.append(await test_vastai_public_api())

    # Test credential validation
    test_results.append(await test_credential_validation())

    # Final analysis
    print("\n" + "=" * 70)
    print("🏆 FINAL REAL DATA VERIFICATION RESULTS")
    print("=" * 70)

    passed = sum(test_results)
    total = len(test_results)

    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed / total * 100):.1f}%")
    print()
    print("🌐 LIVE DATA ANALYSIS:")
    print(f"   ✅ Providers with Real Live Data: {live}")
    print(f"   📦 Providers with Mock Data: {mock}")
    print(f"   ❌ Providers with Errors: {errors}")
    print()

    if live >= 3:  # At least 3 providers with real data
        print("🎉 EXCELLENT! Multiple providers returning real live data!")
        print("🚀 System is actively fetching from real provider APIs!")
    elif live >= 1:
        print("✅ GOOD! At least one provider returning live data!")
        print("🔧 System is partially connected to real APIs!")
    else:
        print("⚠️  WARNING: No providers returning real live data!")
        print("📦 System appears to be using only mock/demo data!")

    if passed == total:
        print("🎊 ALL SYSTEMS WORKING! Provider data acquisition is fully functional!")
        return 0
    else:
        print("⚠️  Some issues detected. Check output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
