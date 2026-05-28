from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apps.api.deps import get_automation_service, get_remarkable_lifecycle_service
from apps.api.routes.automation import router as automation_router
from apps.api.routes.remarkable_sync import router as remarkable_router


class _AutomationService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def status(self, scheduler=None) -> dict:
        return {"scheduler": {"enabled": False}, "latest_run": None}

    async def run_nightly_pipeline(self, **kwargs) -> dict:
        self.calls.append({"method": "nightly", **kwargs})
        return {"ok": True, "kwargs": kwargs}

    async def run_month_rollover(self, from_month: str, to_month: str, *, dry_run: bool) -> dict:
        self.calls.append(
            {
                "method": "rollover",
                "from_month": from_month,
                "to_month": to_month,
                "dry_run": dry_run,
            }
        )
        return {"from_month": from_month, "to_month": to_month, "dry_run": dry_run}


class _LifecycleService:
    def get_current_document_name(self, month: str) -> str:
        return "01. Habit Tracker"

    def get_archive_document_name(self, month: str) -> str:
        return f"{month} Habit Dashboard"

    def get_current_target_path(self, month: str) -> str:
        return "01. Habit Tracker.pdf"

    def get_archive_target_path(self, month: str) -> str:
        return f"HabitOS/{month[:4]}/Archive/{month} Habit Dashboard.pdf"


async def test_automation_routes_pass_through_queries() -> None:
    app = FastAPI()
    app.include_router(automation_router)
    app.include_router(remarkable_router)
    automation = _AutomationService()
    lifecycle = _LifecycleService()
    app.dependency_overrides[get_automation_service] = lambda: automation
    app.dependency_overrides[get_remarkable_lifecycle_service] = lambda: lifecycle

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        status = await client.get("/automation/status")
        assert status.status_code == 200
        assert status.json()["scheduler"]["enabled"] is False

        nightly = await client.post("/automation/nightly-run?dry_run=false")
        assert nightly.status_code == 200
        assert nightly.json()["kwargs"] == {"dry_run": False, "triggered_by": "manual"}

        rollover = await client.post(
            "/automation/month-rollover?from_month=2026-05&to_month=2026-06&dry_run=true"
        )
        assert rollover.status_code == 200
        assert rollover.json() == {
            "from_month": "2026-05",
            "to_month": "2026-06",
            "dry_run": True,
        }

        paths = await client.get("/remarkable/paths?month=2026-06")
        assert paths.status_code == 200
        assert paths.json() == {
            "month": "2026-06",
            "current": {
                "name": "01. Habit Tracker",
                "path": "01. Habit Tracker.pdf",
            },
            "archive": {
                "name": "2026-06 Habit Dashboard",
                "path": "HabitOS/2026/Archive/2026-06 Habit Dashboard.pdf",
            },
            "machine_owned_root": "HabitOS",
        }
