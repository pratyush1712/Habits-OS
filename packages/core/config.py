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


class JournalingRule(_Strict):
    # MVP: any entry that day counts as "checked." Raise this later if the user
    # decides a single thought doesn't count.
    checked_min_entries: int = 1


class MedicationRule(_Strict):
    # Scheduled medications/supplements are checked when all recorded expected
    # doses for the day are taken. PRN/as-needed doses are counted when logged,
    # but absence of a PRN dose is not treated as missed.
    count_prn_without_schedule: bool = True


class ProteinShakeRule(_Strict):
    # Protein shakes are a manual-only log: a day is checked once at least this
    # many shakes are recorded. Absence of a log is simply blank, not missed.
    checked_min_count: int = 1


class HabitRuleConfig(_Strict):
    workout: WorkoutRule = WorkoutRule()
    meditation: MeditationRule = MeditationRule()
    sleep: SleepRule = SleepRule()
    recovery: RecoveryRule = RecoveryRule()
    journaling: JournalingRule = JournalingRule()
    medication: MedicationRule = MedicationRule()
    protein_shake: ProteinShakeRule = ProteinShakeRule()


DEFAULT_RULES = HabitRuleConfig()
