from __future__ import annotations

from apps.api.config import load_settings


def test_load_settings_uses_automation_defaults(monkeypatch):
    monkeypatch.delenv("HABITOS_SCHEDULER_ENABLED", raising=False)
    monkeypatch.delenv("HABITOS_NIGHTLY_RUN_HOUR", raising=False)
    monkeypatch.delenv("HABITOS_NIGHTLY_RUN_MINUTE", raising=False)
    monkeypatch.delenv("HABITOS_RECONCILE_DAYS", raising=False)
    monkeypatch.delenv("HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID", raising=False)
    monkeypatch.delenv("HABITOS_AUTO_UPLOAD_REMARKABLE", raising=False)
    monkeypatch.delenv("HABITOS_REMARKABLE_DRY_RUN", raising=False)

    settings = load_settings()

    assert settings.scheduler_enabled is False
    assert settings.nightly_run_hour == 3
    assert settings.nightly_run_minute == 0
    assert settings.reconcile_days == 14
    assert settings.default_whoop_external_user_id == ""
    assert settings.auto_upload_remarkable is False
    assert settings.remarkable_dry_run is True


def test_load_settings_parses_automation_overrides(monkeypatch):
    monkeypatch.setenv("HABITOS_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("HABITOS_NIGHTLY_RUN_HOUR", "4")
    monkeypatch.setenv("HABITOS_NIGHTLY_RUN_MINUTE", "30")
    monkeypatch.setenv("HABITOS_RECONCILE_DAYS", "21")
    monkeypatch.setenv("HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID", "whoop-user-1")
    monkeypatch.setenv("HABITOS_AUTO_UPLOAD_REMARKABLE", "true")
    monkeypatch.setenv("HABITOS_REMARKABLE_DRY_RUN", "false")

    settings = load_settings()

    assert settings.scheduler_enabled is True
    assert settings.nightly_run_hour == 4
    assert settings.nightly_run_minute == 30
    assert settings.reconcile_days == 21
    assert settings.default_whoop_external_user_id == "whoop-user-1"
    assert settings.auto_upload_remarkable is True
    assert settings.remarkable_dry_run is False
