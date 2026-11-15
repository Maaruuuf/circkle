from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USERNAME_PATTERN = r"^[a-z0-9_]{3,30}$"


def _strip_and_lowercase(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


class StrictModel(BaseModel):
    # Unknown fields are rejected, so nobody can sneak in e.g. {"role": "admin"}.
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictModel):
    email: EmailStr
    username: str = Field(pattern=USERNAME_PATTERN)
    # Never strip a password. The max length stops huge-input abuse of the hasher.
    password: str = Field(min_length=8, max_length=128)

    _normalize = field_validator("email", "username", mode="before")(_strip_and_lowercase)


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    _normalize = field_validator("email", mode="before")(_strip_and_lowercase)


class EmailRequest(StrictModel):
    email: EmailStr

    _normalize = field_validator("email", mode="before")(_strip_and_lowercase)


class TokenRequest(StrictModel):
    token: str = Field(min_length=10, max_length=200)


class ResetPasswordRequest(StrictModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class DeactivateRequest(StrictModel):
    # Required when the account has a password; ignored for Google-only accounts.
    password: str | None = Field(default=None, max_length=128)


class DeleteAccountRequest(StrictModel):
    password: str | None = Field(default=None, max_length=128)
    confirm_username: str = Field(min_length=1, max_length=30)

    _normalize = field_validator("confirm_username", mode="before")(_strip_and_lowercase)


class MessageResponse(BaseModel):
    message: str
