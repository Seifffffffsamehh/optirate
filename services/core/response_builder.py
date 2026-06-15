"""
Response builder — constructs consistent API response envelopes.

All API endpoints in OptiRate return JSON responses following a uniform
envelope structure.  This module provides helper functions to build those
envelopes so route handlers don't need to assemble dicts manually.

Success envelope::

    {
        "status":  "success",
        "message": "<human-readable summary>",
        "data":    <payload>,
        "count":   <int>          # optional — included when explicitly passed
    }

Error envelope::

    {
        "status":  "error",
        "message": "<human-readable error description>"
    }

Usage::

    from services.core.response_builder import success, error

    return jsonify(success("Rates fetched", rates, count=len(rates))), 200
    return jsonify(error("Currency not found")), 404
"""


def success(message: str, data, count: int | None = None) -> dict:
    """
    Build a unified success response dict.

    Args:
        message: Human-readable summary of the operation (e.g. "Rates fetched").
        data:    The response payload — can be a list, dict, or any
                 JSON-serializable value.
        count:   Optional item count.  When provided, a ``"count"`` key is
                 added to the envelope for convenience (avoids the caller
                 needing to inspect ``len(data)``).

    Returns:
        Dict ready to be passed to ``flask.jsonify()``.
    """
    resp = {
        "status": "success",
        "message": message,
        "data": data,
    }
    if count is not None:
        resp["count"] = count
    return resp


def error(message: str) -> dict:
    """
    Build a unified error response dict.

    Args:
        message: Human-readable error description shown to the client.

    Returns:
        Dict ready to be passed to ``flask.jsonify()``.
    """
    return {
        "status": "error",
        "message": message,
    }
