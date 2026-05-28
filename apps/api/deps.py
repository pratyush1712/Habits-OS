"""FastAPI dependency providers.

The DB handle is set on `app.state` by the lifespan. Every other dependency
(repos, services) is constructed per request from that single handle, which
makes it trivial to override `get_db` in tests if needed.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, Request

from packages.core.repositories import (
    AutomationRunsRepo,
    HabitEntriesRepo,
    HabitsRepo,
    ManualOverridesRepo,
    RenderJobsRepo,
    SourceAccountsRepo,
    SourceEventsRepo,
)
from packages.remarkable_sync import (
    ManualRemarkableSyncAdapter,
    RemarkableSyncAdapter,
    RmapiConfig,
    RmapiRemarkableSyncAdapter,
)

from apps.api.services import (
    AutomationService,
    DayOneSyncService,
    EventIngestionService,
    HabitCatalogService,
    HabitEvaluationService,
    MonthStateService,
    PipelineService,
    RenderService,
    RemarkableLifecycleService,
    RemarkableSyncService,
    StatusService,
    WhoopSyncService,
)


def get_db(request: Request):
    return request.app.state.db


def get_output_dir(request: Request) -> Path:
    return request.app.state.output_dir


def get_settings(request: Request):
    return request.app.state.settings


# ---------- repositories ----------


def get_events_repo(db=Depends(get_db)) -> SourceEventsRepo:
    return SourceEventsRepo(db)


def get_overrides_repo(db=Depends(get_db)) -> ManualOverridesRepo:
    return ManualOverridesRepo(db)


def get_entries_repo(db=Depends(get_db)) -> HabitEntriesRepo:
    return HabitEntriesRepo(db)


def get_jobs_repo(db=Depends(get_db)) -> RenderJobsRepo:
    return RenderJobsRepo(db)


def get_automation_runs_repo(db=Depends(get_db)) -> AutomationRunsRepo:
    return AutomationRunsRepo(db)


def get_habits_repo(db=Depends(get_db)) -> HabitsRepo:
    return HabitsRepo(db)


def get_accounts_repo(db=Depends(get_db)) -> SourceAccountsRepo:
    return SourceAccountsRepo(db)


# ---------- services ----------


def get_ingestion(
    events_repo: SourceEventsRepo = Depends(get_events_repo),
    overrides_repo: ManualOverridesRepo = Depends(get_overrides_repo),
    habits_repo: HabitsRepo = Depends(get_habits_repo),
) -> EventIngestionService:
    return EventIngestionService(events_repo, overrides_repo, habits_repo)


def get_evaluation(
    events_repo: SourceEventsRepo = Depends(get_events_repo),
    overrides_repo: ManualOverridesRepo = Depends(get_overrides_repo),
    habits_repo: HabitsRepo = Depends(get_habits_repo),
    entries_repo: HabitEntriesRepo = Depends(get_entries_repo),
) -> HabitEvaluationService:
    return HabitEvaluationService(events_repo, overrides_repo, habits_repo, entries_repo)


def get_habit_catalog(
    habits_repo: HabitsRepo = Depends(get_habits_repo),
) -> HabitCatalogService:
    return HabitCatalogService(habits_repo)


def get_month_state(
    habits_repo: HabitsRepo = Depends(get_habits_repo),
    entries_repo: HabitEntriesRepo = Depends(get_entries_repo),
) -> MonthStateService:
    return MonthStateService(habits_repo, entries_repo)


def get_render_service(
    jobs_repo: RenderJobsRepo = Depends(get_jobs_repo),
    month_state: MonthStateService = Depends(get_month_state),
    output_dir: Path = Depends(get_output_dir),
) -> RenderService:
    return RenderService(jobs_repo, month_state, output_dir)


def get_whoop_sync_service(
    request: Request,
    accounts_repo: SourceAccountsRepo = Depends(get_accounts_repo),
    events_repo: SourceEventsRepo = Depends(get_events_repo),
    evaluation: HabitEvaluationService = Depends(get_evaluation),
) -> WhoopSyncService:
    return WhoopSyncService(
        request.app.state.settings.whoop,
        accounts_repo,
        events_repo,
        evaluation,
    )


def get_dayone_sync_service(
    request: Request,
    events_repo: SourceEventsRepo = Depends(get_events_repo),
    evaluation: HabitEvaluationService = Depends(get_evaluation),
) -> DayOneSyncService:
    return DayOneSyncService(
        request.app.state.settings.dayone,
        events_repo,
        evaluation,
    )


def build_remarkable_adapter_from_state(state) -> RemarkableSyncAdapter:
    settings = state.settings.remarkable
    if settings.adapter == "rmapi":
        config_path = (
            Path(settings.rmapi_config_path)
            if settings.rmapi_config_path
            else None
        )
        return RmapiRemarkableSyncAdapter(
            RmapiConfig(
                binary=settings.rmapi_binary,
                config_path=config_path,
                timeout_seconds=settings.rmapi_timeout_seconds,
                trace=settings.rmapi_trace,
                replace_existing_current=settings.rmapi_replace_existing_current,
                preserve_annotations=settings.rmapi_preserve_annotations,
                machine_root=settings.machine_root,
            )
        )
    return ManualRemarkableSyncAdapter()


def get_remarkable_adapter(request: Request) -> RemarkableSyncAdapter:
    return build_remarkable_adapter_from_state(request.app.state)


def get_remarkable_sync_service(
    jobs_repo: RenderJobsRepo = Depends(get_jobs_repo),
    adapter: RemarkableSyncAdapter = Depends(get_remarkable_adapter),
) -> RemarkableSyncService:
    return RemarkableSyncService(jobs_repo, adapter=adapter)


def get_remarkable_lifecycle_service(
    output_dir: Path = Depends(get_output_dir),
    adapter: RemarkableSyncAdapter = Depends(get_remarkable_adapter),
) -> RemarkableLifecycleService:
    return RemarkableLifecycleService(adapter=adapter, output_dir=output_dir)


def get_status_service(
    request: Request,
    accounts_repo: SourceAccountsRepo = Depends(get_accounts_repo),
    jobs_repo: RenderJobsRepo = Depends(get_jobs_repo),
) -> StatusService:
    return StatusService(request.app.state.db, request.app.state.settings, accounts_repo, jobs_repo)


def get_pipeline_service(
    whoop: WhoopSyncService = Depends(get_whoop_sync_service),
    evaluation: HabitEvaluationService = Depends(get_evaluation),
    render: RenderService = Depends(get_render_service),
    remarkable: RemarkableSyncService = Depends(get_remarkable_sync_service),
) -> PipelineService:
    return PipelineService(whoop, evaluation, render, remarkable)


def build_automation_service_from_state(state) -> AutomationService:
    db = state.db
    output_dir: Path = state.output_dir
    settings = state.settings
    events_repo = SourceEventsRepo(db)
    overrides_repo = ManualOverridesRepo(db)
    habits_repo = HabitsRepo(db)
    entries_repo = HabitEntriesRepo(db)
    jobs_repo = RenderJobsRepo(db)
    accounts_repo = SourceAccountsRepo(db)
    runs_repo = AutomationRunsRepo(db)
    evaluation = HabitEvaluationService(events_repo, overrides_repo, habits_repo, entries_repo)
    month_state = MonthStateService(habits_repo, entries_repo)
    render = RenderService(jobs_repo, month_state, output_dir)
    adapter = build_remarkable_adapter_from_state(state)
    lifecycle = RemarkableLifecycleService(adapter=adapter, output_dir=output_dir)
    whoop = WhoopSyncService(settings.whoop, accounts_repo, events_repo, evaluation)
    dayone = DayOneSyncService(settings.dayone, events_repo, evaluation)
    return AutomationService(
        settings=settings,
        whoop=whoop,
        habits=evaluation,
        render=render,
        lifecycle=lifecycle,
        runs_repo=runs_repo,
        dayone=dayone,
    )


def get_automation_service(request: Request) -> AutomationService:
    return build_automation_service_from_state(request.app.state)
