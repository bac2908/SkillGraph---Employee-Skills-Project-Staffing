from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.api.auth_dependencies import (
    COOKIE_NAME,
    Admin,
    CurrentUser,
    Store,
    verify_origin,
)
from app.core.config import settings
from app.repositories.auth_store import csrf_for
from app.schemas.auth import (
    Login,
    PasswordChange,
    PasswordReset,
    SessionRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.schemas.common import Page
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def clear_cookie(response: Response):
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


def client_address(request: Request) -> str:
    # Forwarded IP headers are deliberately not accepted here.
    return request.client.host if request.client else "unknown"


def validate_grants(role: str, project_ids: list[str]):
    if role != "MANAGER" and project_ids:
        raise HTTPException(422, "Chỉ Manager mới cần danh sách dự án quản lý.")
    for project_id in project_ids:
        ProjectService().get(project_id)


@router.post(
    "/login", response_model=SessionRead, dependencies=[Depends(verify_origin)]
)
def login(payload: Login, request: Request, response: Response, store: Store):
    user, token = store.login(
        str(payload.email),
        payload.password.get_secret_value(),
        client_address(request),
        request.cookies.get(COOKIE_NAME),
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.auth_session_hours * 3600,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"user": user, "csrf_token": csrf_for(token)}


@router.get("/me", response_model=SessionRead)
def me(request: Request, user: CurrentUser):
    return {"user": user, "csrf_token": csrf_for(request.cookies[COOKIE_NAME])}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, store: Store, user: CurrentUser):
    store.logout(request.cookies[COOKIE_NAME])
    clear_cookie(response)


@router.post("/password", status_code=204)
def change_password(
    payload: PasswordChange,
    request: Request,
    response: Response,
    store: Store,
    user: CurrentUser,
):
    store.change_password(
        user["user_id"],
        payload.current_password.get_secret_value(),
        payload.new_password.get_secret_value(),
        client_address(request),
    )
    clear_cookie(response)


@router.get("/users", response_model=Page[UserRead])
def list_users(
    store: Store,
    admin: Admin,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return store.list_users(limit, offset)


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, store: Store, admin: Admin):
    validate_grants(payload.role, payload.project_ids)
    data = payload.model_dump(exclude={"password"})
    data["password"] = payload.password.get_secret_value()
    return store.create_user(data)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(user_id: str, payload: UserUpdate, store: Store, admin: Admin):
    validate_grants(payload.role, payload.project_ids)
    return store.update_user(user_id, payload.model_dump(), admin["user_id"])


@router.post("/users/{user_id}/password", status_code=204)
def reset_password(user_id: str, payload: PasswordReset, store: Store, admin: Admin):
    if user_id == admin["user_id"]:
        raise HTTPException(409, "Hãy dùng chức năng đổi mật khẩu của bạn.")
    store.reset_password(user_id, payload.password.get_secret_value())
