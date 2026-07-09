from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, error_code=error_code)


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource already exists", error_code: str = "CONFLICT"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, error_code=error_code)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request", error_code: str = "BAD_REQUEST"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, error_code=error_code)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Insufficient permissions", error_code: str = "FORBIDDEN"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, error_code=error_code)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Not authenticated", error_code: str = "UNAUTHORIZED"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, error_code=error_code)
