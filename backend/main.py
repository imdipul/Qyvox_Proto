"""Qyvox FastAPI verifier.

Supabase PostgreSQL schema (also available as ``supabase/schema.sql``):

    create table public.verified_users (
        user_id uuid primary key references auth.users(id) on delete cascade,
        verified_at timestamptz not null default timezone('utc', now()),
        proof_hash text not null unique check (proof_hash ~ '^[0-9a-f]{64}$')
    );

There is deliberately no age, birth-year, or date-of-birth column. ``proof_hash``
is a one-way SHA-256 fingerprint used to reject exact proof replays; it is not a
demographic attribute.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import Client, create_client

BASE_DIR = Path(__file__).resolve().parent
DECIMAL_SCALAR_PATTERN = r"^[0-9]{1,80}$"
VERIFY_ENDPOINT_PATHS = frozenset({"/verify", "/api/v1/verify"})


class Settings(BaseSettings):
    """Environment-backed service configuration with safe local defaults."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str
    supabase_service_role_key: SecretStr
    frontend_origins: str = "http://localhost:3000"
    node_binary: str = "node"
    verifier_script: Path = BASE_DIR / "verify.mjs"
    verification_key_path: Path = BASE_DIR / "zk" / "verification_key.json"
    verification_timeout_seconds: float = Field(default=20.0, gt=0, le=60)
    verifier_concurrency: int = Field(default=2, ge=1, le=16)
    max_request_bytes: int = Field(default=32_768, ge=4_096, le=1_048_576)
    expected_current_year: int | None = Field(default=None, ge=2000, le=65_535)

    @property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.frontend_origins.split(",")]
        clean_origins = [origin for origin in origins if origin]
        if not clean_origins or "*" in clean_origins:
            raise ValueError("FRONTEND_ORIGINS must contain exact origins, not '*'.")
        return clean_origins

    @property
    def current_year(self) -> int:
        return self.expected_current_year or datetime.now(timezone.utc).year


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key.get_secret_value(),
    )


Scalar = Annotated[str, Field(pattern=DECIMAL_SCALAR_PATTERN)]


class Groth16Proof(BaseModel):
    """Strict SnarkJS Groth16/bn128 proof shape."""

    model_config = ConfigDict(extra="forbid")

    pi_a: Annotated[list[Scalar], Field(min_length=3, max_length=3)]
    pi_b: Annotated[list[list[Scalar]], Field(min_length=3, max_length=3)]
    pi_c: Annotated[list[Scalar], Field(min_length=3, max_length=3)]
    protocol: Literal["groth16"]
    curve: Literal["bn128"]

    @field_validator("pi_b")
    @classmethod
    def validate_pi_b_shape(cls, rows: list[list[str]]) -> list[list[str]]:
        if any(len(row) != 2 for row in rows):
            raise ValueError("pi_b must contain exactly three two-coordinate rows")
        return rows


class VerifyRequest(BaseModel):
    """Only fields accepted in the POST body; unknown fields fail validation."""

    model_config = ConfigDict(extra="forbid")

    proof: Groth16Proof
    # The camelCase attribute intentionally mirrors the SnarkJS wire format and
    # avoids an alias layer at FastAPI's validation boundary.
    publicSignals: Annotated[list[Scalar], Field(min_length=2, max_length=2)]


class VerificationTraceStep(BaseModel):
    """One server-side operation measured during this exact request."""

    component: Literal["policy", "replay", "verifier", "database"]
    operation: str
    outcome: Literal["passed", "committed"]
    duration_ms: float = Field(ge=0)


class VerificationTrace(BaseModel):
    """Privacy-safe evidence returned only after successful verification."""

    proof_system: Literal["Groth16"] = "Groth16"
    curve: Literal["BN254 / bn128"] = "BN254 / bn128"
    received_fields: tuple[Literal["proof"], Literal["publicSignals"]] = (
        "proof",
        "publicSignals",
    )
    stored_fields: tuple[
        Literal["user_id"],
        Literal["verified_at"],
        Literal["proof_hash"],
    ] = ("user_id", "verified_at", "proof_hash")
    steps: list[VerificationTraceStep]
    total_ms: float = Field(ge=0)


class VerifyResponse(BaseModel):
    verified: Literal[True]
    verified_at: datetime
    trace: VerificationTrace


class ServiceStatusResponse(BaseModel):
    status: Literal["operational", "degraded"]
    api: Literal["operational"]
    verifier: Literal["operational", "unavailable"]
    database: Literal["operational", "unavailable"]


settings = get_settings()
app = FastAPI(
    title="Qyvox Verifier API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

bearer_scheme = HTTPBearer(auto_error=False)
verifier_slots = asyncio.Semaphore(settings.verifier_concurrency)


@app.middleware("http")
async def reject_oversized_verify_requests(request: Request, call_next: Any) -> Any:
    """Reject clearly oversized bodies before JSON parsing.

    The deployment proxy should enforce the same limit for chunked requests.
    Pydantic's fixed proof shape provides the second application-level bound.
    """

    if request.method == "POST" and request.url.path in VERIFY_ENDPOINT_PATHS:
        raw_length = request.headers.get("content-length")
        if raw_length:
            try:
                content_length = int(raw_length)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid Content-Length header."},
                )
            if content_length > settings.max_request_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={"detail": "Proof payload is too large."},
                )
    return await call_next(request)


def _canonical_payload(payload: VerifyRequest) -> dict[str, Any]:
    return payload.model_dump(mode="json", by_alias=True)


def _proof_fingerprint(payload: VerifyRequest) -> str:
    canonical = json.dumps(
        _canonical_payload(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_public_statement(payload: VerifyRequest) -> None:
    """Bind the proof to the policy the server intends to enforce."""

    # Circom publishes output signals before explicitly public input signals:
    # [isEligible, currentYear].
    is_eligible = int(payload.publicSignals[0])
    proof_year = int(payload.publicSignals[1])
    if is_eligible != 1 or proof_year != settings.current_year:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Proof is not eligible for the current verification period.",
        )


def _run_snarkjs_verifier(payload: VerifyRequest) -> bool:
    """Verify one proof in an isolated, time-bounded Node.js subprocess."""

    if not settings.verifier_script.is_file():
        raise RuntimeError(f"Verifier script not found: {settings.verifier_script}")
    if not settings.verification_key_path.is_file():
        raise RuntimeError(
            f"Verification key not found: {settings.verification_key_path}. "
            "Run circuits/setup.sh first."
        )

    request_json = json.dumps(
        _canonical_payload(payload),
        separators=(",", ":"),
    )
    verifier_environment = os.environ.copy()
    verifier_environment.setdefault("NODE_OPTIONS", "--max-old-space-size=192")

    try:
        completed = subprocess.run(
            [
                settings.node_binary,
                str(settings.verifier_script),
                str(settings.verification_key_path),
            ],
            input=request_json,
            text=True,
            capture_output=True,
            check=False,
            timeout=settings.verification_timeout_seconds,
            cwd=BASE_DIR,
            env=verifier_environment,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Node.js verifier runtime was not found.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Proof verification timed out.") from exc

    if completed.returncode != 0:
        diagnostic = completed.stderr.strip()[:500] or "unknown verifier failure"
        raise RuntimeError(f"SnarkJS verifier failed: {diagnostic}")

    try:
        verdict = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SnarkJS returned a malformed verdict.") from exc
    return verdict == {"valid": True}


async def _authenticated_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> UUID:
    """Resolve the bearer token through Supabase Auth, never a client user ID."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Supabase bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        response = await asyncio.to_thread(
            get_supabase().auth.get_user,
            credentials.credentials,
        )
        if response.user is None:
            raise ValueError("Supabase returned no user")
        return UUID(str(response.user.id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Supabase session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _is_unique_violation(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    return code == "23505" or "23505" in str(exc)


async def _proof_was_consumed(proof_hash: str) -> bool:
    def query() -> Any:
        return (
            get_supabase()
            .table("verified_users")
            .select("user_id")
            .eq("proof_hash", proof_hash)
            .limit(1)
            .execute()
        )

    response = await asyncio.to_thread(query)
    return bool(response.data)


async def _record_verification(user_id: UUID, proof_hash: str) -> datetime:
    verified_at = datetime.now(timezone.utc)

    def insert() -> Any:
        return get_supabase().table("verified_users").insert(
            {
                "user_id": str(user_id),
                "verified_at": verified_at.isoformat(),
                "proof_hash": proof_hash,
            }
        ).execute()

    try:
        await asyncio.to_thread(insert)
    except Exception as exc:
        if _is_unique_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This account or proof has already been verified.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Verification succeeded, but the verification record could not be saved.",
        ) from exc
    return verified_at


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status", response_model=ServiceStatusResponse, include_in_schema=False)
async def service_status() -> ServiceStatusResponse:
    """Return a bounded live-readiness signal without exposing diagnostics."""

    verifier_ready = (
        settings.verifier_script.is_file()
        and settings.verification_key_path.is_file()
    )

    def database_probe() -> Any:
        return (
            get_supabase()
            .table("verified_users")
            .select("user_id")
            .limit(1)
            .execute()
        )

    database_ready = True
    try:
        await asyncio.wait_for(asyncio.to_thread(database_probe), timeout=3.0)
    except Exception:
        database_ready = False

    return ServiceStatusResponse(
        status=(
            "operational"
            if verifier_ready and database_ready
            else "degraded"
        ),
        api="operational",
        verifier="operational" if verifier_ready else "unavailable",
        database="operational" if database_ready else "unavailable",
    )


@app.post("/verify", include_in_schema=False)
@app.post(
    "/api/v1/verify",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Missing or invalid Supabase session"},
        403: {"description": "False, invalid, or stale proof"},
        409: {"description": "Account or exact proof already consumed"},
    },
)
async def verify_age(
    payload: VerifyRequest,
    user_id: Annotated[UUID, Depends(_authenticated_user_id)],
) -> VerifyResponse:
    """Verify a proof and persist only the privacy-minimal result."""

    request_started = time.perf_counter()
    trace_steps: list[VerificationTraceStep] = []

    phase_started = time.perf_counter()
    _validate_public_statement(payload)
    trace_steps.append(
        VerificationTraceStep(
            component="policy",
            operation="Bind public eligibility signal to the current policy epoch",
            outcome="passed",
            duration_ms=round((time.perf_counter() - phase_started) * 1000, 3),
        )
    )

    phase_started = time.perf_counter()
    proof_hash = _proof_fingerprint(payload)

    try:
        if await _proof_was_consumed(proof_hash):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This proof has already been used.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Replay protection is temporarily unavailable.",
        ) from exc
    trace_steps.append(
        VerificationTraceStep(
            component="replay",
            operation="Fingerprint the proof and check the consumed-proof index",
            outcome="passed",
            duration_ms=round((time.perf_counter() - phase_started) * 1000, 3),
        )
    )

    async with verifier_slots:
        phase_started = time.perf_counter()
        try:
            is_valid = await asyncio.to_thread(_run_snarkjs_verifier, payload)
        except RuntimeError as exc:
            # Configuration and runtime errors are server failures, not bad proofs.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The proof verifier is temporarily unavailable.",
            ) from exc
    trace_steps.append(
        VerificationTraceStep(
            component="verifier",
            operation="Launch the isolated SnarkJS process and verify against the pinned key",
            outcome="passed",
            duration_ms=round((time.perf_counter() - phase_started) * 1000, 3),
        )
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The zero-knowledge proof is invalid.",
        )

    phase_started = time.perf_counter()
    verified_at = await _record_verification(user_id, proof_hash)
    trace_steps.append(
        VerificationTraceStep(
            component="database",
            operation="Commit the UUID, timestamp, and replay fingerprint receipt",
            outcome="committed",
            duration_ms=round((time.perf_counter() - phase_started) * 1000, 3),
        )
    )

    return VerifyResponse(
        verified=True,
        verified_at=verified_at,
        trace=VerificationTrace(
            steps=trace_steps,
            total_ms=round((time.perf_counter() - request_started) * 1000, 3),
        ),
    )
