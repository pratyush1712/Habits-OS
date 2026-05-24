"""HabitOS MongoDB repositories.

Every repo accepts an `AsyncDatabase`, takes/returns Pydantic models, and is
the *only* layer allowed to know about BSON, `_id`, or ObjectId.
"""

from packages.core.repositories.automation_runs import AutomationRunsRepo
from packages.core.repositories.habit_entries import HabitEntriesRepo
from packages.core.repositories.habits import HabitsRepo
from packages.core.repositories.manual_overrides import ManualOverridesRepo
from packages.core.repositories.render_jobs import RenderJobsRepo
from packages.core.repositories.source_accounts import SourceAccountsRepo
from packages.core.repositories.source_events import SourceEventsRepo

__all__ = [
    "AutomationRunsRepo",
    "HabitEntriesRepo",
    "HabitsRepo",
    "ManualOverridesRepo",
    "RenderJobsRepo",
    "SourceAccountsRepo",
    "SourceEventsRepo",
]
