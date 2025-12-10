from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.users.schemas import UserCreate, UserAuth, UserUpdate, UserRead, AuthResponse, RefreshRequest
from src.users.service import IUserService
from src.users.deps import get_user_service, get_current_user

users_router = APIRouter(prefix="", tags=["Auth"])


@users_router.post("/auth/register", response_model=UserRead, status_code=201)
def register_user(
    payload: UserCreate,
    service: IUserService = Depends(get_user_service),
):
    return service.register_user(payload)


@users_router.post("/auth/login", response_model=AuthResponse)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: IUserService = Depends(get_user_service),
):
    user = UserAuth(email=form_data.username, password=form_data.password)
    return service.login_user(user)


@users_router.post("/auth/refresh", response_model=AuthResponse)
def refresh_tokens(
    payload: RefreshRequest,
    service: IUserService = Depends(get_user_service),
):
    return service.refresh_tokens(payload.refresh_token)


@users_router.get("/auth/me", response_model=UserRead)
def get_me(current_user: UserRead = Depends(get_current_user)):
    return current_user


@users_router.patch("/users/me", response_model=UserRead)
def update_me(
    data: UserUpdate,
    current_user: UserRead = Depends(get_current_user),
    service: IUserService = Depends(get_user_service),
):
    return service.update_user(current_user.id, data)


@users_router.delete("/users/me", status_code=204)
def delete_me(
    current_user: UserRead = Depends(get_current_user),
    service: IUserService = Depends(get_user_service),
):
    service.delete_user(current_user.id)
    return
