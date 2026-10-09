import hmac
import logging
import os
from datetime import datetime
from time import monotonic
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from or_trace.api.schemas import AccountInput, EntityInput, IngestInput, IngestOutput, TraceOutput
from or_trace.domain.models import Account, Entity, Transaction
from or_trace.infrastructure.audit import LoggingAuditSink
from or_trace.infrastructure.memory import Conflict, MemoryLedger
from or_trace.services.ingestion import IngestionService
from or_trace.services.tracing import TraceService


def create_app(ledger=None, audit=None, api_key=None, environment=None):
    environment = environment or os.getenv("OR_TRACE_ENV", "development")
    api_key = api_key if api_key is not None else os.getenv("OR_TRACE_API_KEY", "")
    if environment != "development" and not api_key:
        raise RuntimeError("OR_TRACE_API_KEY is required outside development")
    if environment != "development" and ledger is None:
        raise RuntimeError("A durable Ledger adapter is required outside development")
    app = FastAPI(title="OR TRACE", version="0.1.0")
    app.state.ledger = ledger if ledger is not None else MemoryLedger()
    audit = audit if audit is not None else LoggingAuditSink()
    ingestion = IngestionService(app.state.ledger)
    tracing = TraceService(app.state.ledger)
    app.state.metrics = {"requests": 0, "errors": 0, "duration_seconds": 0.0}

    def authorize(request: Request):
        supplied = request.headers.get("x-api-key", "")
        if api_key and not hmac.compare_digest(supplied, api_key):
            raise HTTPException(401, "invalid credentials")

    @app.middleware("http")
    async def observe(request, call_next):
        request.state.correlation_id = str(uuid4())
        started = monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Correlation-ID"] = request.state.correlation_id
            return response
        finally:
            duration = monotonic() - started
            app.state.metrics["requests"] += 1
            app.state.metrics["errors"] += int(status >= 500)
            app.state.metrics["duration_seconds"] += duration
            audit.record(
                {
                    "correlation_id": request.state.correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_seconds": duration,
                    "timestamp": datetime.now().astimezone().isoformat(),
                    "principal": "service-key" if api_key else "development",
                }
            )

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(
            status_code=409 if isinstance(exc, Conflict) else 422, content={"detail": str(exc)}
        )

    @app.get("/health/live")
    def health():
        return {"status": "ok"}

    @app.get("/metrics", dependencies=[Depends(authorize)], response_class=PlainTextResponse)
    def metrics():
        values = app.state.metrics
        return (
            f"or_trace_requests_total {values['requests']}\n"
            f"or_trace_errors_total {values['errors']}\n"
            f"or_trace_request_duration_seconds_sum {values['duration_seconds']}\n"
        )

    @app.post("/v1/entities", dependencies=[Depends(authorize)], status_code=201)
    def entity(body: EntityInput):
        app.state.ledger.add_entity(Entity(**body.model_dump()))
        return {"id": body.id}

    @app.post("/v1/accounts", dependencies=[Depends(authorize)], status_code=201)
    def account(body: AccountInput):
        app.state.ledger.add_account(Account(**body.model_dump()))
        return {"id": body.id}

    @app.post("/v1/transactions", dependencies=[Depends(authorize)], response_model=IngestOutput)
    def ingest(body: IngestInput, request: Request):
        transactions = [Transaction(**tx.model_dump()) for tx in body.transactions]
        count = ingestion.ingest(transactions, request.state.correlation_id)
        return {"accepted": count, "duplicates": len(transactions) - count}

    @app.get(
        "/v1/accounts/{account_id}/trace",
        dependencies=[Depends(authorize)],
        response_model=TraceOutput,
    )
    def trace(
        account_id: str,
        start: datetime,
        end: datetime,
        currency: str = Query(..., pattern=r"^[A-Z]{3}$"),
        direction: str = Query("forward", pattern="^(forward|backward)$"),
        max_hops: int = Query(5, ge=1, le=10),
        max_paths: int = Query(100, ge=1, le=1000),
    ):
        if start.utcoffset() is None or end.utcoffset() is None:
            raise HTTPException(422, "timestamps require timezone")
        try:
            return tracing.trace(account_id, direction, start, end, currency, max_hops, max_paths)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc

    return app


logging.basicConfig(level=logging.INFO, format="%(message)s")
app = create_app()
