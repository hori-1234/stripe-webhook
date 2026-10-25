import os
import hmac
from flask import Blueprint, render_template, request, abort
from admin_auth import admin_required
from syuwa.syuwa_db import create_syuwa_invite

syuwa_bp = Blueprint(
    "syuwa",
    __name__,
    url_prefix="/syuwa",
    template_folder="templates"
)

@syuwa_bp.route("/admin/invites", methods=["GET"])
@admin_required
def syuwa_admin_invites():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>手話アプリ 招待管理</title>
    </head>
    <body>
        <h2>手話アプリ 招待管理</h2>
        <p>管理者認証に成功しました。</p>
        <p>ここに招待URL発行機能を追加します。</p>
    </body>
    </html>
    """

@syuwa_bp.route("/apply", methods=["GET"])
def syuwa_apply():
    invite_code = request.args.get("code", "")
    expected_code = os.environ.get("SYUWA_INVITE_CODE", "")

    if not expected_code:
        abort(503)

    if not hmac.compare_digest(invite_code, expected_code):
        abort(403)

    return render_template("syuwa_apply.html")
