import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler 
from slowapi.errors import RateLimitExceeded 

from app.api.v1.audit_summary import router as audit_summary_router 
from app.api.v1.questionnaire import router as questionnaire_router  
from app.core.body_limit import BodySizeLimitMiddleware  
from app.core.rate_limit import limiter  

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
_docs_enabled = os.getenv("ENABLE_API_DOCS", "false").lower() == "true"

app = FastAPI(
    title="AI Tax Credit & Compliance Auditor",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

#Rate limiting (slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

#CORS: explicit origins from env
_allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(
    BodySizeLimitMiddleware,
    max_body_bytes=int(os.getenv("MAX_REQUEST_BODY_BYTES", "65536")),
)

app.include_router(questionnaire_router, prefix="/api/v1")
app.include_router(audit_summary_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Tax Auditor Backend"}
