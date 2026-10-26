from flask import Blueprint, jsonify
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

    return jsonify(check_region_headers())
