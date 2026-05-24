"""Verify that ensure_indexes builds every declared index and is idempotent."""

from __future__ import annotations

from packages.core.indexes import INDEX_SPECS, ensure_indexes


async def test_ensure_indexes_creates_all_declared_indexes(db):
    created = await ensure_indexes(db)

    for coll_name, specs in INDEX_SPECS.items():
        assert coll_name in created
        expected = {s.document["name"] for s in specs}
        assert expected.issubset(set(created[coll_name]))

        # Also assert the indexes exist on the live collection.
        index_info = await db[coll_name].index_information()
        for name in expected:
            assert name in index_info, f"missing index {name} on {coll_name}"


async def test_ensure_indexes_is_idempotent(db):
    first = await ensure_indexes(db)
    second = await ensure_indexes(db)
    assert first == second
