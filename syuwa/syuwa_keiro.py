import os
import hmac
from flask import Blueprint, render_template, request, abort

syuwa_bp = Blueprint(
    "syuwa",
    __name__,
    url_prefix="/syuwa",
    template_folder="templates"
)


@syuwa_bp.route("/apply", methods=["GET"])
def syuwa_apply():
    invite_code = request.args.get("code", "")
    expected_code = os.environ.get("SYUWA_INVITE_CODE", "")

    if not expected_code:
        abort(503)

    if not hmac.compare_digest(invite_code, expected_code):
        abort(403)

    return render_template("syuwa_apply.html")
