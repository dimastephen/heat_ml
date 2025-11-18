

class DomainError(Exception):
    code = "domain error"
    http_status = 400
    def __init__(self, message: str = "",*, code: str | None = None, extra: dict | None = None):
        super().__init__(message)
        self.code = code or self.code
        self.extra = extra or {}


class ValidationError(DomainError):
    code = "validation error"
    http_status = 400


class AuthError(DomainError):
    code = "auth error"
    http_status = 401


class PermissionDenied(DomainError):
    code = "forbidden"
    http_status = 403


class NotFoundError(DomainError):
    code = "not_found"
    http_status = 404


class ConflictError(DomainError):
    code = "conflict"
    http_status = 409