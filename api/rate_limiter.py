"""
IP-based rate limiting using SlowAPI.

Two shared limit pools:
  - "separation_pool": 5 requests/day per IP (all Demucs separation endpoints)
  - "youtube_pool":    5 requests/day per IP (all YouTube download endpoints)

Uses in-memory storage (resets on container restart).
"""

from starlette.requests import Request
from starlette.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded


def get_client_ip(request: Request) -> str:
    """Extract client IP, respecting reverse proxy headers from HF Spaces nginx."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[],
    headers_enabled=True,
    storage_uri="memory://",
)

separation_limit = limiter.shared_limit(
    "5/day",
    scope="separation_pool",
    error_message="Daily separation limit reached (5/day). Please try again tomorrow.",
)

youtube_limit = limiter.shared_limit(
    "5/day",
    scope="youtube_pool",
    error_message="Daily YouTube download limit reached (5/day). Please try again tomorrow.",
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    detail = str(exc.detail) if exc.detail else "Rate limit exceeded"
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": detail,
            "detail": (
                "This is a free service with limited GPU resources. "
                "Each IP address is allowed 5 separation requests and "
                "5 YouTube downloads per day. Limits reset daily."
            ),
        },
    )
