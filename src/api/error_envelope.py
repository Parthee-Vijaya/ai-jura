"""Konsistent error-envelope for hele Bifrost-API'et.

I dag returnerer de 59+ spredte `raise HTTPException(...)` forskellige
shapes alt efter hvad sagsbehandleren har gjort. Det betyder at frontend
skal probe på `.detail` vs `.message` vs `.error.detail`, og uncaught
exceptions giver en helt fjerde form.

Denne modul tilbyder:

1. `error_response(code, message, status, details, hint)` — helper
   der altid producerer samme shape:
   {
     "error": {
       "code": "string-stable-id",          # snake_case identifier
       "message": "Human-readable text",    # vises typisk i toast
       "details": {...} | null,             # struktureret kontekst
       "hint": "..." | null,                # forslag til løsning
       "trace_id": "uuid" | null,           # for korrelation med logs
       "timestamp": "ISO-8601"
     }
   }

2. `register_error_handlers(app)` — registrerer globale handlers så
   HTTPException, RequestValidationError og uncaught Exception alle
   producerer samme shape.

Brug:

  from src.api.error_envelope import error_response, AppError

  # Typed (anbefalet)
  raise AppError("evidens_not_found", "Evidens findes ikke", status=404,
                 details={"artifact_id": artifact_id},
                 hint="Tjek at sagen har den her evidens i evidens-fanen")

  # Eller helper direkte
  raise HTTPException(status_code=404, detail=error_envelope(
      "evidens_not_found",
      "Evidens findes ikke",
  ))
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("bifrost.errors")


# ---- Core helpers ---------------------------------------------------------


def error_envelope(
    code: str,
    message: str,
    *,
    details: Optional[dict[str, Any]] = None,
    hint: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict[str, Any]:
    """Returnér en error-dict i Bifrosts standardformat.

    Kan bruges som `detail=` på HTTPException eller wrappet direkte i
    JSONResponse via de globale handlers.
    """
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "hint": hint,
            "trace_id": trace_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    }


# ---- Typed exception ------------------------------------------------------


class AppError(HTTPException):
    """Bifrost-typed HTTPException der altid producerer error-envelope-shape.

    Brug i stedet for `HTTPException` så frontend kan stole på struct'en.

    Eksempel:
        raise AppError(
            "case_not_found",
            f"Sag {case_id} findes ikke",
            status=404,
            details={"case_id": case_id},
            hint="Tjek case_id under /sager",
        )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        details: Optional[dict[str, Any]] = None,
        hint: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        super().__init__(
            status_code=status,
            detail=error_envelope(code, message, details=details, hint=hint),
            headers=headers,
        )
        self.code = code
        self.message = message


# ---- Globale exception-handlers ------------------------------------------


async def http_exception_handler(request: Request, exc: HTTPException):
    """Catch-all for HTTPException — wrap'er legacy `detail`-string-form
    i error-envelope hvis det ikke allerede er det.

    Sikrer bagudkompatibilitet med de 59 legacy `raise HTTPException(detail="...")`
    indtil de gradvist migreres til AppError.
    """
    trace_id = getattr(request.state, "request_id", None)

    # Hvis detail allerede ER vores envelope-shape, send det igennem
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        body = exc.detail
        # Injicér trace_id hvis ikke sat
        if not body["error"].get("trace_id") and trace_id:
            body["error"]["trace_id"] = trace_id
    else:
        # Legacy form — wrap det i envelope
        # Best-effort code-mapping fra status-koden
        code_map = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "validation_error",
            429: "rate_limited",
            500: "internal_error",
            502: "upstream_error",
            503: "service_unavailable",
            504: "upstream_timeout",
        }
        code = code_map.get(exc.status_code, f"http_{exc.status_code}")
        message = str(exc.detail) if exc.detail else "Ukendt fejl"
        body = error_envelope(code, message, trace_id=trace_id)

    return JSONResponse(status_code=exc.status_code, content=body)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """Pydantic validation-fejl → standardiseret envelope med felt-detaljer."""
    trace_id = getattr(request.state, "request_id", None)

    # Pydantic giver en liste af errors — pak dem ind i details
    details = {
        "validation_errors": [
            {
                "field": ".".join(str(p) for p in err.get("loc", [])),
                "message": err.get("msg"),
                "type": err.get("type"),
            }
            for err in exc.errors()
        ]
    }
    body = error_envelope(
        "validation_error",
        "Anmodningen er ugyldig — tjek payload mod schema",
        details=details,
        hint="Se 'validation_errors' for hver felt-fejl",
        trace_id=trace_id,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for alt der ikke er HTTPException — undgår 500 med bare stack-trace.

    Logger fuld traceback men returnerer kun et stable error_id til frontend
    så vi ikke leak'er intern info (CWE-209: Information Exposure Through
    an Error Message).
    """
    trace_id = getattr(request.state, "request_id", None) or "unknown"
    logger.exception(
        "Unhandled exception",
        extra={
            "trace_id": trace_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    body = error_envelope(
        "internal_error",
        "Der opstod en intern fejl",
        details=None,  # bevidst tom — fejlinfo ligger kun i log
        hint=f"Kontakt IT med trace_id={trace_id} hvis fejlen gentager sig",
        trace_id=trace_id,
    )
    return JSONResponse(status_code=500, content=body)


# ---- Public registration --------------------------------------------------


def register_error_handlers(app: FastAPI) -> None:
    """Registrér alle handlers på app'en.

    Skal kaldes EFTER limiter-handler er sat op, så rate-limit-errors stadig
    bruger slowapi's dedicated handler.

    Kaldsmønster i main.py:
        from src.api.error_envelope import register_error_handlers
        register_error_handlers(app)
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
