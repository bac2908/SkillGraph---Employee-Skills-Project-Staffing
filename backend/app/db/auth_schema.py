"""Shared shape checks, not migrations or bootstrap logic."""

AUTH_COLUMNS = {
    "users": "user_id, email, name, password_hash, role, is_active, must_change_password, project_ids",
    "sessions": "token_hash, user_id, created_at, expires_at, last_seen",
    "login_limits": "key, window_start, attempts",
}
