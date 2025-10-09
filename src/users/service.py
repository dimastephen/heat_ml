from abc import ABC,abstractmethod
from typing import Dict, Optional

from src.users.database import IUserRepository
from src.users.schemas import UserCreate, UserRead, UserAuth, UserUpdate, AuthResponse
from src.core.security import hash_password,verify_password, create_access_token, create_refresh_token, verify_token


class IUserService(ABC):

    @abstractmethod
    def register_user(self,user:UserCreate) -> UserRead:
        raise NotImplementedError

    @abstractmethod
    def login_user(self, user: UserAuth) -> AuthResponse:
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_user(self, user_id: int, user: UserUpdate)-> UserRead:
        raise NotImplementedError

    @abstractmethod
    def user_get_id(self, id: int) -> Optional[UserRead]:
        raise NotImplementedError


class UserService(IUserService):
    def __init__(self, repo: IUserRepository):
        self.repo = repo

    def register_user(self, user: UserCreate) -> UserRead:
        existing = self.repo.get_by_email(user.email)
        if existing:
            raise ValueError(f"User {user.email} already exists")

        hashed_password = hash_password(user.password)
        db_user = self.repo.create({
            "email": user.email,
            "password": hashed_password
        })

        return UserRead.model_validate(db_user)

    def login_user(self, user: UserAuth) -> AuthResponse:
        db_existing = self.repo.get_by_email(user.email)
        if not db_existing or not verify_password(existing.password, user.password):
            raise ValueError("Invalid email or password")
        access_token = create_access_token({"sub":str(db_existing.id)})
        refresh_token = create_refresh_token({"sub":str(db_existing.id)})
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserRead.model_validate(db_existing)
        )

