class AppError(Exception):
    status_code = 500


class EmailAlreadyRegisteredError(AppError):
    status_code = 409
