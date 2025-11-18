from pydantic import BaseModel, EmailStr, field_validator


class User(BaseModel):
    email: EmailStr


class UserCreate(User):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must include letters and numbers or symbols")
        return v


class UserAuth(User):
    password: str
    @field_validator("password")
    @classmethod
    def validate_password_not_empty(cls, v: str):
        if not v:
            raise ValueError("Password cannot be empty")
        return v


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str | None):
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must include letters and numbers or symbols")
        return v


class UserRead(User):
    id: int | None = None

    class Config:
        from_attributes=True


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead
