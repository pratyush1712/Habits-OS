from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apps.api.deps import get_events_repo
from apps.api.routes.events import router


class _EventsRepo:
    def __init__(self) -> None:
        self.events = []

    async def upsert_many_counts(self, events):
        self.events = list(events)
        return {"inserted": len(self.events), "updated": 0, "total": len(self.events)}


async def test_log_medication_events_normalizes_dose_counts() -> None:
    app = FastAPI()
    app.include_router(router)
    repo = _EventsRepo()
    app.dependency_overrides[get_events_repo] = lambda: repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/events/medication",
            json={
                "local_date": "2026-05-31",
                "timezone": "America/New_York",
                "doses": [
                    {
                        "med_key": "magnesium",
                        "med_label": "Magnesium",
                        "taken_count": 1,
                        "scheduled_count": 2,
                        "prn": False,
                    },
                    {
                        "med_key": "hydroxyzine",
                        "med_label": "Hydroxyzine",
                        "taken_count": 0,
                        "scheduled_count": 0,
                        "prn": True,
                    },
                ],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-05",
        "local_date": "2026-05-31",
        "events": 2,
        "inserted": 2,
        "updated": 0,
    }
    assert [event.id for event in repo.events] == [
        "manual:med-2026-05-31-magnesium",
        "manual:med-2026-05-31-hydroxyzine",
    ]
    magnesium = repo.events[0]
    assert magnesium.event_type == "medication"
    assert magnesium.source == "manual"
    assert magnesium.local_date.isoformat() == "2026-05-31"
    assert magnesium.timezone == "America/New_York"
    assert magnesium.metrics == {
        "med_key": "magnesium",
        "med_label": "Magnesium",
        "taken_count": 1,
        "scheduled_count": 2,
        "prn": False,
    }


async def test_log_medication_events_rejects_unknown_timezone() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_events_repo] = lambda: _EventsRepo()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/events/medication",
            json={
                "local_date": "2026-05-31",
                "timezone": "Not/AZone",
                "doses": [
                    {
                        "med_key": "magnesium",
                        "med_label": "Magnesium",
                        "taken_count": 1,
                        "scheduled_count": 2,
                    }
                ],
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown timezone"


async def test_log_protein_shake_event_normalizes_count() -> None:
    app = FastAPI()
    app.include_router(router)
    repo = _EventsRepo()
    app.dependency_overrides[get_events_repo] = lambda: repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/events/protein-shake",
            json={
                "local_date": "2026-06-09",
                "timezone": "America/New_York",
                "count": 2,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-06",
        "local_date": "2026-06-09",
        "count": 2,
        "inserted": 1,
        "updated": 0,
    }
    assert [event.id for event in repo.events] == [
        "manual:protein-shake-2026-06-09",
    ]
    shake = repo.events[0]
    assert shake.event_type == "protein_shake"
    assert shake.source == "manual"
    assert shake.local_date.isoformat() == "2026-06-09"
    assert shake.timezone == "America/New_York"
    assert shake.metrics == {"count": 2}


async def test_log_protein_shake_event_defaults_to_one() -> None:
    app = FastAPI()
    app.include_router(router)
    repo = _EventsRepo()
    app.dependency_overrides[get_events_repo] = lambda: repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/events/protein-shake",
            json={"local_date": "2026-06-09"},
        )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert repo.events[0].metrics == {"count": 1}


async def test_log_protein_shake_event_rejects_unknown_timezone() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_events_repo] = lambda: _EventsRepo()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/events/protein-shake",
            json={
                "local_date": "2026-06-09",
                "timezone": "Not/AZone",
                "count": 1,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown timezone"


async def test_log_intake_event_normalizes_itemized_substances() -> None:
    app = FastAPI()
    app.include_router(router)
    repo = _EventsRepo()
    app.dependency_overrides[get_events_repo] = lambda: repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/events/intake",
            json={
                "local_date": "2026-06-09",
                "timezone": "America/New_York",
                "items": [
                    {
                        "key": "everyday_dose_coffee_plus_lions_mane",
                        "label": "Everyday Dose Coffee+ — Lion's Mane",
                        "brand_key": "everyday_dose",
                        "brand_label": "Everyday Dose",
                        "product_key": "everyday_dose_coffee_plus",
                        "product_label": "Everyday Dose Coffee+",
                        "ingredient_key": "lions_mane",
                        "ingredient_label": "Lion's Mane Fruiting Body Extract",
                        "category": "mushroom",
                        "amount": 1,
                        "unit": "serving",
                        "caffeine_mg": 45,
                        "time_of_day": "morning",
                    },
                    {
                        "key": "ryze_mushroom_hot_cocoa_glycine",
                        "label": "RYZE Mushroom Hot Cocoa — Glycine",
                        "brand_key": "ryze",
                        "brand_label": "RYZE",
                        "product_key": "ryze_mushroom_hot_cocoa",
                        "product_label": "RYZE Mushroom Hot Cocoa",
                        "ingredient_key": "glycine",
                        "ingredient_label": "Glycine",
                        "category": "amino_acid",
                        "time_of_day": "night",
                        "notes": "night cup",
                    },
                ],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-06",
        "local_date": "2026-06-09",
        "items": 2,
        "inserted": 2,
        "updated": 0,
    }
    assert [event.id for event in repo.events] == [
        "manual:intake-2026-06-09-everyday_dose_coffee_plus_lions_mane-morning",
        "manual:intake-2026-06-09-ryze_mushroom_hot_cocoa_glycine-night",
    ]
    intake = repo.events[0]
    assert intake.event_type == "intake"
    assert intake.source == "manual"
    assert intake.local_date.isoformat() == "2026-06-09"
    assert intake.timezone == "America/New_York"
    assert intake.title == "Everyday Dose Coffee+ — Lion's Mane"
    assert intake.metrics["count"] == 1
    assert intake.metrics["items"][0]["brand_label"] == "Everyday Dose"
    assert intake.metrics["items"][0]["ingredient_label"] == "Lion's Mane Fruiting Body Extract"
    assert repo.events[1].metrics["items"][0]["product_label"] == "RYZE Mushroom Hot Cocoa"
    assert repo.events[1].metrics["items"][0]["time_of_day"] == "night"


async def test_log_intake_event_same_day_logs_accumulate_by_item() -> None:
    app = FastAPI()
    app.include_router(router)

    class _AccumulatingRepo(_EventsRepo):
        async def upsert_many_counts(self, events):
            by_id = {event.id: event for event in self.events}
            inserted = 0
            updated = 0
            for event in events:
                if event.id in by_id:
                    updated += 1
                else:
                    inserted += 1
                by_id[event.id] = event
            self.events = list(by_id.values())
            return {"inserted": inserted, "updated": updated, "total": inserted + updated}

    repo = _AccumulatingRepo()
    app.dependency_overrides[get_events_repo] = lambda: repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/events/intake",
            json={
                "local_date": "2026-06-09",
                "items": [
                    {
                        "key": "everyday_dose_coffee_plus_lions_mane",
                        "label": "Everyday Dose Coffee+ — Lion's Mane",
                        "time_of_day": "morning",
                    }
                ],
            },
        )
        second = await client.post(
            "/events/intake",
            json={
                "local_date": "2026-06-09",
                "items": [
                    {
                        "key": "ryze_mushroom_hot_cocoa_glycine",
                        "label": "RYZE Mushroom Hot Cocoa — Glycine",
                        "time_of_day": "night",
                    }
                ],
            },
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["inserted"] == 1
    assert {event.id for event in repo.events} == {
        "manual:intake-2026-06-09-everyday_dose_coffee_plus_lions_mane-morning",
        "manual:intake-2026-06-09-ryze_mushroom_hot_cocoa_glycine-night",
    }
    labels = {event.metrics["items"][0]["label"] for event in repo.events}
    assert labels == {
        "Everyday Dose Coffee+ — Lion's Mane",
        "RYZE Mushroom Hot Cocoa — Glycine",
    }


async def test_log_intake_event_rejects_unknown_timezone() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_events_repo] = lambda: _EventsRepo()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/events/intake",
            json={
                "local_date": "2026-06-09",
                "timezone": "Not/AZone",
                "items": [{"key": "cuppa", "label": "Cuppa Coffee"}],
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown timezone"


async def test_log_medication_events_can_be_listed_by_date() -> None:
    app = FastAPI()
    app.include_router(router)
    repo = _EventsRepo()

    async def list_events(**kwargs):
        return [
            event
            for event in repo.events
            if kwargs.get("event_type") in (None, event.event_type)
            and (kwargs.get("start") is None or event.local_date >= kwargs["start"])
            and (kwargs.get("end") is None or event.local_date <= kwargs["end"])
        ]

    repo.list_events = list_events
    app.dependency_overrides[get_events_repo] = lambda: repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        save = await client.post(
            "/events/medication",
            json={
                "local_date": "2026-05-31",
                "timezone": "America/New_York",
                "doses": [
                    {
                        "med_key": "magnesium",
                        "med_label": "Magnesium",
                        "taken_count": 2,
                        "scheduled_count": 2,
                    }
                ],
            },
        )
        listed = await client.get(
            "/events",
            params={
                "start": "2026-05-31",
                "end": "2026-05-31",
                "event_type": "medication",
            },
        )

    assert save.status_code == 200
    assert listed.status_code == 200
    events = listed.json()
    assert len(events) == 1
    assert events[0]["metrics"]["med_key"] == "magnesium"
    assert events[0]["metrics"]["taken_count"] == 2
