from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic import BaseModel, ValidationError

from magaza_core import contracts
from magaza_core.money import format_try
from magaza_core.sse import encode_sse

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"
BUNDLE = json.loads((CONTRACTS_DIR / "generated" / "bundle.schema.json").read_text(encoding="utf-8"))
VALID = json.loads((CONTRACTS_DIR / "examples" / "valid.json").read_text(encoding="utf-8"))
INVALID = json.loads((CONTRACTS_DIR / "examples" / "invalid.json").read_text(encoding="utf-8"))


def _schema_validator(name: str) -> jsonschema.protocols.Validator:
    schema = {"$ref": f"#/$defs/{name}", "$defs": BUNDLE["$defs"]}
    return jsonschema.Draft202012Validator(schema)


def _parse(name: str, value: Any) -> Any:
    if name == "SseEvent":
        return contracts.SSE_EVENT_ADAPTER.validate_python(value)
    model: type[BaseModel] = getattr(contracts, name)
    return model.model_validate(value)


def test_bundle_is_valid_json_schema() -> None:
    jsonschema.Draft202012Validator.check_schema(BUNDLE)


@pytest.mark.parametrize(("name", "value"), [(n, v) for n, vs in VALID.items() for v in vs])
def test_valid_examples_pass_schema_and_pydantic(name: str, value: Any) -> None:
    _schema_validator(name).validate(value)
    parsed = _parse(name, value)
    # Round trip: dumping the model must validate against the schema again.
    _schema_validator(name).validate(json.loads(parsed.model_dump_json(exclude_none=True)))


@pytest.mark.parametrize(("name", "value"), [(n, v) for n, vs in INVALID.items() for v in vs])
def test_invalid_examples_fail_schema_and_pydantic(name: str, value: Any) -> None:
    assert not _schema_validator(name).is_valid(value)
    with pytest.raises(ValidationError):
        _parse(name, value)


def test_chat_request_rejects_client_supplied_tenant() -> None:
    with pytest.raises(ValidationError):
        contracts.ChatRequest.model_validate(
            {"message": "x", "visitor_id": "v_12345678", "tenant_id": "ambalaj"}
        )


def test_event_type_literal_matches_schema() -> None:
    assert set(contracts.ANALYTICS_EVENT_TYPES) == set(BUNDLE["$defs"]["AnalyticsEventType"]["enum"])


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1234.9, "₺1.234,90"), (0, "₺0,00"), (19.99, "₺19,99"), (1234567.891, "₺1.234.567,89"), (-5, "-₺5,00")],
)
def test_format_try(value: float, expected: str) -> None:
    assert format_try(value) == expected


def test_encode_sse() -> None:
    wire = encode_sse(contracts.TokenEvent(type="token", text="Merhaba")).decode()
    assert wire == 'event: token\ndata: {"type":"token","text":"Merhaba"}\n\n'
