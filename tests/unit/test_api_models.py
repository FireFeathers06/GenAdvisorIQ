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
    assert resp["success"] is False
    assert resp["data"] is None
    assert resp["error"]["code"] == "NOT_FOUND"
    assert resp["error"]["message"] == "Resource not found"


def test_success_response_generates_request_id_when_missing():
    resp = success_response({})
    assert len(resp["meta"]["request_id"]) == 36  # UUID4 length
