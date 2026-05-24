from apps.api.routes import (
    events,
    habit_entries,
    habits,
    health,
    render,
    state,
    whoop,
)

ROUTERS = [
    health.router,
    events.router,
    habits.router,
    habit_entries.router,
    state.router,
    render.router,
    whoop.router,
]
