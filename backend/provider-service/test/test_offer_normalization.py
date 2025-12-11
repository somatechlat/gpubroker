"""
Property 2: Provider Offer Normalization Consistency
Validates: Requirements 2.2, 2.5
"""

import pytest
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.normalized_offer import NormalizedOffer


def test_normalized_offer_validates_and_coerces():
    offer = NormalizedOffer(
        provider="runpod",
        region="us-east",
        gpu_type="A100",
        price_per_hour=2.5,
        currency="usd",
        availability_status="AVAILABLE",
        compliance_tags=["soc2", 123],
        gpu_memory_gb=80,
        cpu_cores=16,
        ram_gb=64,
        storage_gb=1000,
        external_id="A100:us-east",
        tokens_per_second=8000,
        last_updated=datetime.now(timezone.utc),
    )

    assert offer.availability_status == "available"
    assert offer.currency == "usd"  # lowercased preserved
    assert offer.price_per_hour == 2.5
    assert offer.compliance_tags == ["soc2", "123"]


def test_normalized_offer_rejects_negative_price():
    with pytest.raises(Exception):
        NormalizedOffer(
            provider="runpod",
            region="us-east",
            gpu_type="A100",
            price_per_hour=-1.0,
            external_id="A100:us-east",
        )


def test_normalized_offer_rejects_bad_availability():
    with pytest.raises(Exception):
        NormalizedOffer(
            provider="runpod",
            region="us-east",
            gpu_type="A100",
            price_per_hour=1.0,
            availability_status="maybe",
            external_id="A100:us-east",
        )


@given(
    price=st.floats(min_value=0, max_value=1000, allow_infinity=False, allow_nan=False),
    mem=st.integers(min_value=0, max_value=96),
)
@settings(max_examples=25)
def test_normalized_offer_property_non_negative(price, mem):
    offer = NormalizedOffer(
        provider="vastai",
        region="us-west",
        gpu_type="V100",
        price_per_hour=price,
        gpu_memory_gb=mem,
        external_id="V100:us-west",
    )
    assert offer.price_per_hour >= 0
    assert offer.gpu_memory_gb >= 0
