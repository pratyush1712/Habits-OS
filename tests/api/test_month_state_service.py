from datetime import date, datetime, timezone

from apps.api.services.month_state import MonthStateService
from packages.core.models import Habit, HabitEntry, SourceEvent


class _HabitsRepo:
    async def list_active(self):
        return [Habit(key="medication", label="Medication", short="Rx")]


class _EntriesRepo:
    async def list_by_month(self, month: str):
        return [
            HabitEntry(
                date=date(2026, 6, 7),
                habit_key="medication",
                status="checked",
                source="manual",
            )
        ]


class _EventsRepo:
    async def list_by_month(self, month: str):
        return [
            SourceEvent(
                id="manual:med-2026-06-07-magnesium",
                source="manual",
                source_event_id="med-2026-06-07-magnesium",
                event_type="medication",
                start_time_utc=datetime(2026, 6, 7, 16, tzinfo=timezone.utc),
                local_date=date(2026, 6, 7),
                title="Magnesium",
                metrics={
                    "med_key": "magnesium",
                    "taken_count": 2,
                    "scheduled_count": 2,
                },
            ),
            SourceEvent(
                id="manual:med-2026-06-07-hydroxyzine",
                source="manual",
                source_event_id="med-2026-06-07-hydroxyzine",
                event_type="medication",
                start_time_utc=datetime(2026, 6, 7, 16, tzinfo=timezone.utc),
                local_date=date(2026, 6, 7),
                title="Hydroxyzine",
                metrics={
                    "med_key": "hydroxyzine",
                    "taken_count": 1,
                    "scheduled_count": 0,
                    "prn": True,
                },
            ),
        ]


async def test_month_state_includes_medication_days_from_source_events() -> None:
    service = MonthStateService(_HabitsRepo(), _EntriesRepo(), _EventsRepo())

    state = await service.get_state("2026-06")

    by_med = {dose.med_key: dose for dose in state.medication_days}
    assert state.medication_groups
    assert by_med["magnesium"].date == date(2026, 6, 7)
    assert by_med["magnesium"].taken == 2
    assert by_med["magnesium"].total == 2
    assert by_med["hydroxyzine"].taken == 1
    assert by_med["hydroxyzine"].total == 0
