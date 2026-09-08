import secrets
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie

from app.core.config import settings
from app.repositories.auth_store import AuthStore, csrf_for

COOKIE_NAME = "skillgraph_session"
cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@lru_cache
def get_auth_store() -> AuthStore:
    return AuthStore(
        settings.auth_db_path,
        settings.auth_session_hours * 3600,
        settings.auth_idle_minutes * 60,
    )


Store = Annotated[AuthStore, Depends(get_auth_store)]


def verify_origin(request: Request):
    # Never trust forwarded/Host headers for CSRF allowlisting.
    if request.headers.get("origin") not in settings.auth_allowed_origins:
        raise HTTPException(403, "Nguồn yêu cầu không được phép.")


def current_user(
    request: Request,
    store: Store,
    token: Annotated[str | None, Depends(cookie_scheme)],
) -> dict:
    if not token or len(token) > 128:
        raise HTTPException(401, "Vui lòng đăng nhập để tiếp tục.")
    user = store.authenticate(token)
    if request.method not in SAFE_METHODS:
        verify_origin(request)
        supplied = request.headers.get("x-csrf-token", "")
        if len(supplied) != 64 or not secrets.compare_digest(
            supplied.encode(), csrf_for(token).encode()
        ):
            raise HTTPException(403, "Phiên bảo vệ không hợp lệ. Hãy tải lại trang.")
    return user


CurrentUser = Annotated[dict, Depends(current_user)]


def require_admin(user: CurrentUser) -> dict:
    if user["must_change_password"]:
        raise HTTPException(403, "Bạn cần đổi mật khẩu trước khi tiếp tục.")
    if user["role"] != "ADMIN":
        raise HTTPException(403, "Chức năng này chỉ dành cho Admin.")
    return user


Admin = Annotated[dict, Depends(require_admin)]


def authorize_business(request: Request, user: CurrentUser):
    """Deny writes by default; allow only explicit manager endpoint functions."""
    if user["must_change_password"]:
        raise HTTPException(403, "Bạn cần đổi mật khẩu trước khi tiếp tục.")
    if request.method in SAFE_METHODS or user["role"] == "ADMIN":
        return
    # Endpoint identity is independent of nested router prefixes.
    from app.api.project_assignments import (
        delete_project_assignment,
        upsert_project_assignment,
    )
    from app.api.project_requirements import (
        delete_project_requirement,
        upsert_project_requirement,
    )
    from app.api.projects import update_project

    manager_routes = {
        ("PATCH", update_project),
        ("PUT", upsert_project_assignment),
        ("DELETE", delete_project_assignment),
        ("PUT", upsert_project_requirement),
        ("DELETE", delete_project_requirement),
    }
    if (
        user["role"] == "MANAGER"
        and (request.method, request.scope.get("endpoint")) in manager_routes
        and request.path_params.get("project_id") in user["project_ids"]
    ):
        return
    raise HTTPException(403, "Bạn không có quyền thay đổi dữ liệu này.")
