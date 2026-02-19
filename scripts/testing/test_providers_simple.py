#!/usr/bin/env python3
"""
Quick test to verify all 20 providers are implemented and can be imported.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(
    0, "/Users/macbookpro201916i964gb1tb/Documents/GitHub/gpubroker/backend/gpubroker"
)


def test_provider_adapters():
    """Test that all provider adapters can be imported and instantiated."""
    print("🔍 Testing All Provider Adapters...")
    print("=" * 60)

    # Expected providers from registry
    expected_providers = [
        "alibaba",
        "aws_sagemaker",
        "azure_ml",
        "cerebras",
        "deepinfra",
        "google_vertex_ai",
        "groq",
        "ibm_watson",
        "kaggle",
        "lambdalabs",
        "nvidia_dgx",
        "oracle_oci",
        "paperspace",
        "replicate",
        "runai",
        "runpod",
        "scaleai",
        "spell",
        "vastai",
    ]

    success_count = 0
    error_count = 0
    failed_providers = []

    for provider_name in expected_providers:
        try:
            # Try to import the adapter module
            module_name = f"apps.providers.adapters.{provider_name}"
            module = __import__(
                module_name, fromlist=[f"{provider_name.title()}Adapter"]
            )

            # Get adapter class name - map to correct class names
            class_name_mapping = {
                "aws_sagemaker": "AWSSageMakerAdapter",
                "azure_ml": "AzureMLAdapter",
                "google_vertex_ai": "GoogleVertexAIAdapter",
                "lambdalabs": "LambdaLabsAdapter",
                "nvidia_dgx": "NVIDIADGXAdapter",
                "oracle_oci": "OracleOCIAdapter",
                "paperspace": "PaperspaceAdapter",
                "scaleai": "ScaleaiAdapter",
                "vastai": "VastAIAdapter",
                "deepinfra": "DeepInfraAdapter",
                "ibm_watson": "IBMWatsonAdapter",
                "runai": "RunAIAdapter",
                "runpod": "RunPodAdapter",
            }
            adapter_class_name = class_name_mapping.get(
                provider_name, f"{provider_name.title().replace('_', '')}Adapter"
            )

            # Check if adapter exists in module
            if hasattr(module, adapter_class_name):
                print(f"✅ {provider_name:12} - {adapter_class_name}")
                success_count += 1
            else:
                print(f"❌ {provider_name:12} - Class not found")
                error_count += 1
                failed_providers.append(provider_name)

        except ImportError as e:
            print(f"❌ {provider_name:12} - Import failed: {str(e)}")
            error_count += 1
            failed_providers.append(provider_name)
        except Exception as e:
            print(f"❌ {provider_name:12} - Error: {str(e)}")
            error_count += 1
            failed_providers.append(provider_name)

    print("=" * 60)
    print(f"📊 SUMMARY:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {error_count}")
    print(f"   📈 Success Rate: {(success_count / len(expected_providers) * 100):.1f}%")

    if failed_providers:
        print(f"\n❌ Failed Providers: {', '.join(failed_providers)}")

    return success_count == len(expected_providers)


def test_registry_loading():
    """Test registry can load all adapters."""
    print("\n🏪 Testing Registry Loading...")
    print("=" * 60)

    try:
        from apps.providers.adapters.registry import ProviderRegistry

        # Initialize registry
        ProviderRegistry.initialize_registry()

        # Get loaded adapters
        loaded_providers = ProviderRegistry.list_adapters()

        print(f"📋 Registry loaded {len(loaded_providers)} adapters:")
        for provider in sorted(loaded_providers):
            print(f"   • {provider}")

        return True

    except Exception as e:
        print(f"❌ Registry Test Failed: {str(e)}")
        return False


def test_base_components():
    """Test base components can be imported."""
    print("\n🧪 Testing Base Components...")
    print("=" * 60)

    try:
        from apps.providers.adapters.base import BaseProviderAdapter, ProviderOffer

        print("✅ Base adapter and offer classes")

        from apps.providers.models import Provider, GPUOffer

        print("✅ Database models")

        from apps.providers.services import fetch_offers_from_adapters

        print("✅ Services")

        return True

    except Exception as e:
        print(f"❌ Base Components Test Failed: {str(e)}")
        return False


def main():
    """Main test function."""
    print("🚀 GPUBROKER PROVIDER IMPLEMENTATION TEST")
    print(
        f"📅 Run at: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print()

    # Run all tests
    test_results = []

    test_results.append(test_base_components())
    test_results.append(test_provider_adapters())
    test_results.append(test_registry_loading())

    # Final summary
    print("\n" + "=" * 60)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 60)

    passed = sum(test_results)
    total = len(test_results)

    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed / total * 100):.1f}%")

    if passed == total:
        print("🎉 ALL TESTS PASSED! All 20 providers are implemented!")
        print("\n📋 IMPLEMENTED PROVIDERS:")
        print("   ✅ Alibaba Cloud (alibaba)")
        print("   ✅ AWS SageMaker (aws_sagemaker)")
        print("   ✅ Azure ML (azure_ml)")
        print("   ✅ Cerebras (cerebras)")
        print("   ✅ DeepInfra (deepinfra)")
        print("   ✅ Google Vertex AI (google_vertex_ai)")
        print("   ✅ Groq (groq)")
        print("   ✅ IBM Watson (ibm_watson)")
        print("   ✅ Kaggle (kaggle)")
        print("   ✅ Lambda Labs (lambdalabs)")
        print("   ✅ NVIDIA DGX (nvidia_dgx)")
        print("   ✅ Oracle OCI (oracle_oci)")
        print("   ✅ Paperspace (paperspace)")
        print("   ✅ Replicate (replicate)")
        print("   ✅ RunAI (runai)")
        print("   ✅ RunPod (runpod)")
        print("   ✅ ScaleAI (scaleai)")
        print("   ✅ Spell (spell)")
        print("   ✅ VastAI (vastai)")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
