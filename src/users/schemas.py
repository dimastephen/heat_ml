from pydantic import BaseModel,EmailStr


class User(BaseModel):
    email: EmailStr


class UserCreate(User):
    password: str


class UserAuth(User):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None


class UserRead(User):
    id: int | None = None

    class Config:
        from_attributes:True


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead