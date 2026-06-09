from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class ApiError(Exception):
    def __init__(self, message: str, code: str = "error", status: int = 400):
        self.message = message
        self.code = code
        self.status = status


def ok(data):
    return {"data": data, "error": None}


def fail(message: str, code: str = "error", status: int = 400):
    return JSONResponse(
        status_code=status,
        content={"data": None, "error": {"message": message, "code": code}},
    )


def register_exception_handlers(app):
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return fail(exc.message, exc.code, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return fail(str(exc), "validation_error", 422)

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        import traceback
        traceback.print_exc()
        return fail(f"Internal server error: {str(exc)}", "internal_error", 500)
