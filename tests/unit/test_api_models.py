import json

from app.models.api import success_response, error_response


def test_success_response_shape():
    resp = success_response({"key": "value"}, request_id="test-id")
    assert resp["success"] is True
    assert resp["data"] == {"key": "value"}
    assert resp["error"] is None
    assert resp["meta"]["request_id"] == "test-id"
    assert "timestamp" in resp["meta"]


def test_error_response_shape():
    resp = error_response("NOT_FOUND", "Resource not found", request_id="test-id")
    body = json.loads(resp.body)
    assert resp.status_code == 500  # unknown code defaults to 500
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Resource not found"


def test_error_response_maps_status_codes():
    assert error_response("CUSTOMER_NOT_FOUND", "x").status_code == 404
    assert error_response("INVALID_ID", "x").status_code == 400
    assert error_response("INVALID_CREDENTIALS", "x").status_code == 401
    assert error_response("SERVER_ERROR", "x").status_code == 500
    assert error_response("ANY", "x", status_code=418).status_code == 418


def test_success_response_generates_request_id_when_missing():
    resp = success_response({})
    assert len(resp["meta"]["request_id"]) == 36  # UUID4 length
