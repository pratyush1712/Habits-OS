"""Default thresholds for the habit rule engine.

Per-habit rule structs are kept small and explicit. Adding a new rule means
adding a struct here, a field on `HabitRuleConfig`, and an evaluator in
`rules.py` — no plugin system, no registry.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkoutRule(_Strict):
    checked_min_minutes: float = 15.0
    partial_min_minutes: float = 5.0


class MeditationRule(_Strict):
    checked_min_minutes: float = 5.0
    partial_min_minutes: float = 2.0


class SleepRule(_Strict):
    target_hours: float = 7.0


class RecoveryRule(_Strict):
    checked_min_score: int = 67


class HabitRuleConfig(_Strict):
    workout: WorkoutRule = WorkoutRule()
    meditation: MeditationRule = MeditationRule()
    sleep: SleepRule = SleepRule()
    recovery: RecoveryRule = RecoveryRule()


DEFAULT_RULES = HabitRuleConfig()
