"""Tests for src.api.error_envelope — standardiseret API-fejlformat."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from src.api.error_envelope import (
    AppError,
    error_envelope,
    register_error_handlers,
)


# ---- Helpers --------------------------------------------------------------


def make_test_app() -> FastAPI:
    """Mini-app der eksponerer hver error-form for testning."""
    app = FastAPI()
    register_error_handlers(app)

    class Item(BaseModel):
        title: str = Field(..., min_length=1, max_length=10)
        count: int = Field(..., ge=1)

    @app.post("/ok")
    def ok_endpoint(item: Item):
        return {"ok": True, "received": item.model_dump()}

    @app.get("/legacy-httpexception")
    def legacy_endpoint():
        # Bagudkompatibilitet — string-detail wrappes til envelope
        raise HTTPException(status_code=404, detail="Sag findes ikke")

    @app.get("/apperror-typed")
    def typed_endpoint():
        raise AppError(
            "case_not_found",
            "Sagen K-2026-9999 findes ikke",
            status=404,
            details={"case_id": "K-2026-9999"},
            hint="Tjek under /sager om id er korrekt",
        )

    @app.get("/uncaught")
    def uncaught_endpoint():
        # Trigger en uncaught exception
        raise ValueError("This is a bug")

    return app


# ---- Tests ----------------------------------------------------------------


def test_envelope_helper_structure():
    """error_envelope() producerer den dokumenterede shape."""
    env = error_envelope("test_code", "Test message")
    assert "error" in env
    err = env["error"]
    assert err["code"] == "test_code"
    assert err["message"] == "Test message"
    assert err["details"] is None
    assert err["hint"] is None
    assert err["trace_id"] is None
    assert err["timestamp"]  # ISO-8601 string


def test_envelope_helper_with_all_fields():
    env = error_envelope(
        "bad_input",
        "Field X is required",
        details={"field": "X"},
        hint="Send X i payload",
        trace_id="abc-123",
    )
    err = env["error"]
    assert err["details"] == {"field": "X"}
    assert err["hint"] == "Send X i payload"
    assert err["trace_id"] == "abc-123"


def test_apperror_produces_envelope():
    """AppError eksponerer .detail i envelope-shape."""
    err = AppError("case_not_found", "Sagen findes ikke", status=404)
    assert err.status_code == 404
    assert isinstance(err.detail, dict)
    assert err.detail["error"]["code"] == "case_not_found"
    assert err.detail["error"]["message"] == "Sagen findes ikke"


def test_apperror_via_endpoint():
    """AppError-typed exception returnerer envelope korrekt."""
    app = make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/apperror-typed")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "case_not_found"
    assert "Sagen K-2026-9999" in body["error"]["message"]
    assert body["error"]["details"] == {"case_id": "K-2026-9999"}
    assert "Tjek under /sager" in body["error"]["hint"]
    assert body["error"]["timestamp"]


def test_legacy_httpexception_wrapped_to_envelope():
    """raise HTTPException(detail='string') wrappes til envelope."""
    app = make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/legacy-httpexception")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"  # mappet fra 404
    assert body["error"]["message"] == "Sag findes ikke"


def test_validation_error_wrapped():
    """Pydantic validation-fejl producerer envelope med felt-detaljer."""
    app = make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/ok", json={"title": "", "count": 0})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]["validation_errors"]
    # Skal indeholde fejl for begge felter
    fields = [e["field"] for e in body["error"]["details"]["validation_errors"]]
    assert any("title" in f for f in fields)
    assert any("count" in f for f in fields)


def test_uncaught_exception_wrapped():
    """Uncaught exception læk'er ikke stack-trace, returnerer pæn envelope."""
    app = make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/uncaught")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Der opstod en intern fejl"
    # Stack-trace skal IKKE være i response (CWE-209 information exposure)
    assert "ValueError" not in str(body)
    assert "This is a bug" not in str(body)


def test_envelope_all_have_timestamp_and_code():
    """Invariant: alle endpoints returnerer ALTID code+message+timestamp."""
    app = make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    for path in ["/apperror-typed", "/legacy-httpexception", "/uncaught"]:
        resp = client.get(path)
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"]
        assert body["error"]["message"]
        assert body["error"]["timestamp"]
