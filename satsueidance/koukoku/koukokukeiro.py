from flask import Blueprint, jsonify, request
from event_schedule.memo_auth import is_schedule_operator
from satsueidance.koukoku.chiiki import check_region_headers

koukoku_bp = Blueprint(
    "koukoku",
    __name__,
    url_prefix="/satsueidance/koukoku"
)


@koukoku_bp.route("/region-test")
def region_test():
    if not is_schedule_operator():
        return jsonify({"error": "Forbidden"}), 403

    result = check_region_headers()

    result["location_headers"] = {
        key: value
        for key, value in request.headers.items()
        if key.lower().startswith("cf-")
        and (
            "country" in key.lower()
            or "region" in key.lower()
            or "city" in key.lower()
            or "postal" in key.lower()
            or "latitude" in key.lower()
            or "longitude" in key.lower()
        )
    }

    result["ip_test"] = {
        "remote_addr": request.remote_addr,
        "x_forwarded_for": request.headers.get("X-Forwarded-For", ""),
        "x_real_ip": request.headers.get("X-Real-IP", ""),
        "cf_connecting_ip": request.headers.get("CF-Connecting-IP", "")
    }

    return jsonify(result)
