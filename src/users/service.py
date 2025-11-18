from abc import ABC, abstractmethod
from typing import Optional

from src.core.errors import ConflictError, AuthError, NotFoundError
from src.core.logger import logger
from src.users.repository import IUserRepository
from src.users.schemas import UserCreate, UserRead, UserAuth, UserUpdate, AuthResponse
from src.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token


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
    def get_current_user(self, token: str) -> Optional[UserRead]:
        raise NotImplementedError

    @abstractmethod
    def refresh_tokens(self, refresh_token:str) -> AuthResponse:
        raise NotImplementedError

class UserService(IUserService):
    def __init__(self, repo: IUserRepository):
        self.repo = repo

    def register_user(self, user: UserCreate) -> UserRead:
        existing = self.repo.get_by_email(user.email)
        if existing:
            raise ConflictError(f"User {user.email} already exists",code="email_taken")

        hashed_password = hash_password(user.password)
        db_user = self.repo.create({
            "email": user.email,
            "hashed_password": hashed_password
        })
        logger.info("User registered", extra={"email": user.email, "user_id": db_user.id})
        return UserRead.model_validate(db_user)

    def login_user(self, user: UserAuth) -> AuthResponse:
        db_existing = self.repo.get_by_email(user.email)
        if not db_existing or not verify_password(db_existing.hashed_password, user.password):
            logger.warning("Login failed", extra={"email": user.email})
            raise AuthError(f"Invalid email or password",code="invalid_credentials")
        access_token = create_access_token({"sub":str(db_existing.id)})
        refresh_token = create_refresh_token({"sub":str(db_existing.id)})
        logger.info("Login succeeded", extra={"email": user.email, "user_id": db_existing.id})
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserRead.model_validate(db_existing)
        )

    def update_user(self, user_id: int, user: UserUpdate) -> UserRead:
        db_user = self.repo.get(user_id)
        if not db_user:
            raise NotFoundError("User Not found")
        update_data = user.model_dump(exclude_unset=True)
        if "password" in update_data:
            hashed_password = hash_password(update_data.pop("password"))
            update_data["hashed_password"] = hashed_password
        updated_user = self.repo.update(db_user,update_data)
        return UserRead.model_validate(updated_user)

    def get_current_user(self, token: str) -> Optional[UserRead]:
        payload = decode_token(token, expected_scope="access")
        if not payload:
            raise AuthError(f"Invalid or expired token",code="invalid_token")
        user_id = int(payload["sub"])
        db_user = self.repo.get(user_id)
        if not db_user:
            raise NotFoundError("User Not found")
        return UserRead.model_validate(db_user)

    def delete_user(self, id: int) -> None:
        db_user = self.repo.get(id)
        if not db_user:
            raise NotFoundError("User Not found")
        self.repo.delete(id)

    def refresh_tokens(self, refresh_token: str):
        payload = decode_token(refresh_token,expected_scope="refresh")
        if not payload:
            logger.warning("Refresh failed: invalid token")
            raise AuthError(f"Invalid or expired refresh token",code="invalid_refresh_token")
        user_id = int(payload["sub"])
        db_user = self.repo.get(user_id)
        if not db_user:
            raise NotFoundError("User Not found")
        new_access_token = create_access_token({"sub": str(user_id)})
        new_refresh_token = create_refresh_token({"sub": str(user_id)})
        logger.info("Refresh succeeded", extra={"user_id": user_id})
        return AuthResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user=UserRead.model_validate(db_user)
        )
