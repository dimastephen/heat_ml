from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.database import get_pg_db
from src.users.repository import IUserRepository, UserRepository
from src.users.service import IUserService,UserService
from src.users.schemas import UserRead
from src.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_user_repo(db: Session = Depends(get_pg_db)) -> IUserRepository:
    return UserRepository(db, User)

def get_user_service(repo: IUserRepository = Depends(get_user_repo)) -> IUserService:
    return UserService(repo)

def get_current_user(
        token: str = Depends(oauth2_scheme),
        service: IUserService = Depends(get_user_service),
) -> UserRead:
    return service.get_current_user(token)
