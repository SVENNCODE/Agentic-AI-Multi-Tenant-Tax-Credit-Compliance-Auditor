import logging
import os

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

load_dotenv()

logger = logging.getLogger(__name__)

security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not set")

SUPABASE_URL = SUPABASE_URL.rstrip("/")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
EXPECTED_ISSUER = f"{SUPABASE_URL}/auth/v1"

# Only asymmetric algorithms. Keys come from the project's public JWKS, so a
# symmetric (HS256) algorithm is never be accepted here
ALLOWED_ALGORITHMS = {"ES256", "RS256", "EdDSA"}

jwks_client = PyJWKClient(JWKS_URL, cache_keys=True, lifespan=600)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired authentication credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        algorithm = signing_key.algorithm_name
        if algorithm not in ALLOWED_ALGORITHMS:
            raise jwt.InvalidAlgorithmError(f"Algorithm {algorithm} not allowed")

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=EXPECTED_ISSUER,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as e:
        # Details go to server logs only — never back to the client.
        logger.info("JWT verification failed: %s", type(e).__name__)
        raise _UNAUTHORIZED
    except Exception:
        logger.exception("Unexpected error during JWT verification")
        raise _UNAUTHORIZED

    if payload.get("role") != "authenticated" or not payload.get("sub"):
        raise _UNAUTHORIZED

    return payload


def bearer_token(credentials: HTTPAuthorizationCredentials) -> str:
    """The raw access token, for building an RLS-scoped Supabase client."""
    return credentials.credentials
