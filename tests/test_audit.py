import importlib

def test_audit_helper_exists():
    mod = importlib.import_module("app.audit")
    assert hasattr(mod, "log_action")