from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.WORKER

    @model_validator(mode="after")
    def validate_contact(self) -> "UserCreate":
        if not self.email and not self.phone:
            raise ValueError("Either email or phone is required")
        return self


class UserLogin(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerify(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class PasswordResetComplete(BaseModel):
    email: EmailStr
    reset_token: str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
