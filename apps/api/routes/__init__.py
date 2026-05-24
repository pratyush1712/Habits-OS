from apps.api.routes import (
    automation,
    events,
    habit_entries,
    habits,
    health,
    pipeline,
    render,
    remarkable_sync,
    state,
    status,
    whoop,
)

ROUTERS = [
    health.router,
    status.router,
    automation.router,
    events.router,
    habits.router,
    habit_entries.router,
    state.router,
    render.router,
    remarkable_sync.router,
    whoop.router,
    pipeline.router,
]
