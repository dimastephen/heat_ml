from abc import ABC, abstractmethod
from typing import Optional
from src.database import BaseRepository, SQLAlchemyRepository
from src.users.models import User


class IUserRepository(BaseRepository[User], ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError


class UserRepository(IUserRepository, SQLAlchemyRepository[User]):
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
