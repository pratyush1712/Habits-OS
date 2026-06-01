"""Unit tests for catalog reconciliation in HabitCatalogService.

These run without Mongo by injecting an in-memory fake repository, so the
retire-on-reseed behavior (e.g. dropping deep_work) is always covered.
"""

from __future__ import annotations

import pytest

from apps.api.services.habit_catalog import HabitCatalogService
from packages.core.default_habits import default_habits
from packages.core.models import Habit


class _FakeHabitsRepo:
    """Minimal in-memory stand-in for HabitsRepo."""

    def __init__(self, habits: list[Habit]) -> None:
        self._docs: dict[str, Habit] = {h.key: h for h in habits}
        self._archived: set[str] = set()

    async def count_all(self) -> int:
        return len(self._docs)

    async def upsert_many(self, habits) -> int:
        n = 0
        for h in habits:
            self._docs[h.key] = h
            self._archived.discard(h.key)
            n += 1
        return n

    async def list_active(self) -> list[Habit]:
        return [
            h
            for k, h in sorted(self._docs.items(), key=lambda kv: kv[1].sort_order)
            if h.enabled and k not in self._archived
        ]

    async def archive(self, key: str) -> bool:
        if key in self._docs and key not in self._archived:
            self._archived.add(key)
            return True
        return False


def _legacy_deep_work() -> Habit:
    return Habit(key="deep_work", label="Deep work", short="D", kind="auto", sort_order=70)


@pytest.mark.asyncio
async def test_seed_reconciles_and_retires_removed_habits():
    # Legacy catalog: the current defaults plus a now-removed deep_work habit.
    repo = _FakeHabitsRepo([*default_habits(), _legacy_deep_work()])
    service = HabitCatalogService(repo)

    result = await service.seed_default_habits()

    assert result["retired"] == ["deep_work"]
    active_keys = {h.key for h in await repo.list_active()}
    assert "deep_work" not in active_keys
    assert active_keys == {h.key for h in default_habits()}
    assert "deep_work" in result["message"]


@pytest.mark.asyncio
async def test_seed_applies_metric_only_flag_to_existing_habits():
    # An old sleep habit stored before metric_only existed (defaults to False).
    stale_sleep = Habit(key="sleep", label="Sleep", short="Z", kind="auto", sort_order=50)
    repo = _FakeHabitsRepo([stale_sleep])
    service = HabitCatalogService(repo)

    await service.seed_default_habits()

    active = {h.key: h for h in await repo.list_active()}
    assert active["sleep"].metric_only is True


@pytest.mark.asyncio
async def test_seed_reports_no_retirements_for_clean_catalog():
    repo = _FakeHabitsRepo(list(default_habits()))
    service = HabitCatalogService(repo)

    result = await service.seed_default_habits()

    assert result["retired"] == []
    assert result["total_active"] == len(default_habits())
