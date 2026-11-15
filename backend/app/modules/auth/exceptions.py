from app.core.errors import BadRequestError, ConflictError, ForbiddenError, UnauthenticatedError


class EmailOrUsernameTakenError(ConflictError):
    code = "EMAIL_OR_USERNAME_TAKEN"
    message = "Email or username is already in use"


class InvalidCredentialsError(UnauthenticatedError):
    code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"  # one message for every login failure


class InvalidRefreshTokenError(UnauthenticatedError):
    code = "INVALID_REFRESH_TOKEN"
    message = "Invalid refresh token"


class InvalidTokenError(BadRequestError):
    code = "INVALID_TOKEN"
    message = "This link is invalid or has expired"


class EmailNotVerifiedError(ForbiddenError):
    code = "EMAIL_NOT_VERIFIED"
    message = "Please verify your email address before logging in"


class AccountDisabledError(ForbiddenError):
    code = "ACCOUNT_DISABLED"
    message = "This account has been disabled"


class IncorrectPasswordError(BadRequestError):
    code = "INCORRECT_PASSWORD"
    message = "The password is incorrect"


class PasswordNotSetError(BadRequestError):
    code = "PASSWORD_NOT_SET"
    message = "This account has no password yet. Use 'Forgot password' to create one"


class ConfirmationMismatchError(BadRequestError):
    code = "CONFIRMATION_MISMATCH"
    message = "The confirmation text does not match your username"
