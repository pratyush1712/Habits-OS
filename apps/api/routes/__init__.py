from apps.api.routes import (
    events,
    habit_entries,
    habits,
    health,
    render,
    state,
)

ROUTERS = [
    health.router,
    events.router,
    habits.router,
    habit_entries.router,
    state.router,
    render.router,
]
