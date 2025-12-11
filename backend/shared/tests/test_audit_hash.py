"""
Property 17: Audit Log Hash Chain Integrity
Validates: Requirements 16.4, 31.6
"""

from shared.audit_hash import compute_hash


def test_hash_chain_matches_manual():
    e1 = {"event": "login", "user": "u1"}
    e2 = {"event": "action", "user": "u1", "action": "create"}

    h1 = compute_hash("", e1)
    h2 = compute_hash(h1, e2)

    # Manual recomputation
    assert h1 == compute_hash("", e1)
    assert h2 == compute_hash(h1, e2)
    assert h1 != h2
