"""
Shared slowapi limiter.

THis is Keyed by the authenticated user (JWT `sub`, read *unverified* only to pick a
bucket the route's own dependency still performs full verification) and
falling back to client IP. Keying on the user in this case means one account cannot
bypass the limit by rotating IPs, and one noisy IP cannot starve others.
"""

import os

import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

QUESTIONNAIRE_RATE_LIMIT = os.getenv("QUESTIONNAIRE_RATE_LIMIT", "5/minute")


def user_or_ip_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            claims = jwt.decode(
                auth[7:], options={"verify_signature": False}, algorithms=None
            )
            sub = claims.get("sub")
            if isinstance(sub, str) and sub:
                return f"user:{sub}"
        except jwt.PyJWTError:
            pass
    return f"ip:{get_remote_address(request)}"


# In-memory by default (per-process). 
# Note for me: For multi-worker / multi-instance
# deployments point this at Redis
RATE_LIMIT_STORAGE_URI = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

limiter = Limiter(
    key_func=user_or_ip_key,
    storage_uri=RATE_LIMIT_STORAGE_URI,
    headers_enabled=True,
)
