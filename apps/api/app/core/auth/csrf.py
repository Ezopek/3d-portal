"""apps/api/app/core/auth/csrf.py — custom-header CSRF defense."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def install_csrf_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def csrf_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method in UNSAFE_METHODS:
            path = request.url.path
            if path.startswith("/api/") and not path.startswith("/api/share/"):
                if request.headers.get("X-Portal-Client") != "web":
                    return JSONResponse({"detail": "csrf_required"}, status_code=403)
        return await call_next(request)
