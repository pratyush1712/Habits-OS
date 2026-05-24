from __future__ import annotations


def test_local_control_surface_routes_registered(monkeypatch):
    monkeypatch.setenv("MONGODB_TEST_URI", "")
    from apps.api.main import create_app

    app = create_app()
    routes = {(method, route.path) for route in app.routes if hasattr(route, "methods") for method in route.methods}

    assert ("GET", "/status") in routes
    assert ("GET", "/habits") in routes
    assert ("POST", "/habits/seed-defaults") in routes
    assert ("GET", "/whoop/status") in routes
    assert ("POST", "/whoop/sync") in routes
    assert ("GET", "/automation/status") in routes
    assert ("POST", "/automation/nightly-run") in routes
    assert ("POST", "/automation/month-rollover") in routes
    assert ("GET", "/remarkable/status") in routes
    assert ("GET", "/remarkable/paths") in routes
    assert ("POST", "/remarkable/upload") in routes
    assert ("POST", "/remarkable/sync") in routes
    assert ("POST", "/pipeline/month") in routes
