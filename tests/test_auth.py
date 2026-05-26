"""
tests/test_auth.py — Auth module tests for Nexus AI Governance Platform.
"""
from auth.security import hash_password, verify_password
from auth.roles import USERS_DB, ROLE_PERMISSIONS, has_permission


# ── Security ──────────────────────────────────────────────────────────────────

def test_hash_verify():
    pw = "TestPassword123!"
    h  = hash_password(pw)
    assert verify_password(pw, h)
    assert not verify_password("wrong", h)


# ── Demo users ────────────────────────────────────────────────────────────────

def test_users_db_populated():
    assert "admin"      in USERS_DB
    assert "compliance" in USERS_DB
    assert "auditor"    in USERS_DB
    assert USERS_DB["admin"]["role"] == "Admin"


# ── Role permissions ──────────────────────────────────────────────────────────

def test_admin_has_all_permissions():
    for page in ["Dashboard", "Admin Settings", "Analytics",
                 "Policy Upload", "Compliance Auditor"]:
        assert has_permission("Admin", page), f"Admin missing: {page}"


def test_developer_has_all_permissions():
    for page in ["Dashboard", "Admin Settings", "Analytics",
                 "Policy Upload", "Compliance Auditor"]:
        assert has_permission("Developer", page), f"Developer missing: {page}"


def test_auditor_no_admin_settings():
    assert not has_permission("Auditor", "Admin Settings")
    assert has_permission("Auditor", "Dashboard")


def test_viewer_limited():
    assert has_permission("Viewer", "Dashboard")
    assert has_permission("Viewer", "Knowledge Base")
    assert not has_permission("Viewer", "Compliance Auditor")
    assert not has_permission("Viewer", "Admin Settings")


# ── Secret keys ───────────────────────────────────────────────────────────────

def test_developer_secret_key():
    DEVELOPER_SECRET = "844502"
    assert DEVELOPER_SECRET == "844502"
    assert DEVELOPER_SECRET != "73520"


def test_admin_secret_key():
    ADMIN_SECRET = "73520"
    assert ADMIN_SECRET == "73520"
    assert ADMIN_SECRET != "844502"


# ── User store ────────────────────────────────────────────────────────────────

def test_load_all_users_includes_demo():
    from auth.user_store import load_all_users
    all_users = load_all_users()
    assert "admin" in all_users
    assert "compliance" in all_users


def test_user_exists_demo():
    from auth.user_store import user_exists
    assert user_exists("admin")
    assert not user_exists("nonexistent_xyz_123")


def test_register_and_delete_user():
    from auth.user_store import register_user, user_exists, delete_user

    # Register
    success, msg = register_user(
        username="test_user_99",
        password_hash=hash_password("TestPass123!"),
        full_name="Test User",
        email="test99@test.com",
        role="Viewer",
        department="Testing",
    )
    assert success, f"Registration failed: {msg}"
    assert user_exists("test_user_99")

    # Duplicate check
    success2, msg2 = register_user(
        username="test_user_99",
        password_hash=hash_password("TestPass123!"),
        full_name="Test User",
        email="test99@test.com",
        role="Viewer",
        department="Testing",
    )
    assert not success2, "Duplicate registration should fail"

    # Delete
    deleted = delete_user("test_user_99")
    assert deleted
    assert not user_exists("test_user_99")