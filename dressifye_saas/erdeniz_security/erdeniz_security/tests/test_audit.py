"""
erdeniz_security/tests/test_audit.py — audit_trail ve export_audit_logs testleri.
"""
import os
import json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "erdeniz_security.tests.settings")
os.environ["ERDENIZ_ENCRYPTION_KEY"] = __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode()

import django
django.setup()

import pytest
from erdeniz_security.audit import audit_trail, export_audit_logs, log_event


@pytest.mark.django_db
def test_audit_trail_success():
    @audit_trail(action="TEST_ACTION", project="test")
    def dummy_func(x):
        return x * 2
    result = dummy_func(5)
    assert result == 10


@pytest.mark.django_db
def test_audit_trail_exception():
    @audit_trail(action="TEST_FAIL", project="test")
    def failing_func():
        raise ValueError("test error")
    with pytest.raises(ValueError):
        failing_func()


@pytest.mark.django_db
def test_export_audit_logs_json():
    log_event("TEST_EVENT", "resource", "test_project", success=True)
    output = export_audit_logs(project="test_project", format="json")
    data = json.loads(output)
    assert "records" in data
    assert isinstance(data["records"], list)


@pytest.mark.django_db
def test_export_audit_logs_csv():
    log_event("TEST_EVENT", "resource", "test_project", success=True)
    output = export_audit_logs(project="test_project", format="csv")
    assert "event_type" in output
