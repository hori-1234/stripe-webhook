from flask import Blueprint, send_from_directory
from pathlib import Path

a_sya_bp = Blueprint(
    "a_sya",
    __name__,
    url_prefix="/a-sya"
)

ARTIST_DIR = Path(__file__).resolve().parent


@a_sya_bp.route("/", methods=["GET"])
def a_sya_submit():
    return send_from_directory(
        str(ARTIST_DIR),
        "a-sya_submit.html"
    )
