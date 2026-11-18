class AppError(Exception):
    status_code = 500


class EmailAlreadyRegisteredError(AppError):
    status_code = 409


class InvalidCredentialsError(AppError):
    status_code = 401


class InactiveUserError(AppError):
    status_code = 403


class InvalidRefreshTokenError(AppError):
    status_code = 401


class InvalidAccessTokenError(AppError):
    status_code = 401


class ProfileAlreadyExistsError(AppError):
    status_code = 409


class ProfileNotFoundError(AppError):
    status_code = 404
