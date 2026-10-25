import os
import hmac
import secrets
from flask import Blueprint, render_template, request, abort, session
from admin_auth import admin_required
from syuwa.syuwa_db import create_syuwa_invite, verify_syuwa_invite

syuwa_bp = Blueprint(
    "syuwa",
    __name__,
    url_prefix="/syuwa",
    template_folder="templates"
)

@syuwa_bp.route("/admin/invites", methods=["GET"])
@admin_required

def syuwa_admin_invites():
    if "syuwa_csrf_token" not in session:
        session["syuwa_csrf_token"] = secrets.token_urlsafe(32)

    csrf_token = session["syuwa_csrf_token"]

    return """
    
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>手話アプリ 招待管理</title>
    </head>
    <body>
        
        <p>管理者認証に成功しました。</p>

        <form method="POST" action="/syuwa/admin/invites/create">
            <input type="hidden" name="csrf_token" value="{csrf_token}">
            <button type="submit">
                個別招待URLを発行
            </button>
        </form>

    </body>
    </html>
    """.replace("{csrf_token}", csrf_token)

@syuwa_bp.route("/admin/invites/create", methods=["POST"])
@admin_required
def syuwa_create_invite():
    submitted_token = request.form.get("csrf_token", "")
    expected_token = session.get("syuwa_csrf_token", "")

    if not expected_token:
        abort(403)

    if not hmac.compare_digest(submitted_token, expected_token):
        abort(403)

    token = create_syuwa_invite()

    invite_url = (
        request.url_root.rstrip("/")
        + "/syuwa/apply?token="
        + token
    )

    return (
        "<h2>個別招待URLを発行しました</h2>"
        "<p>以下のURLを招待する人に送ってください。</p>"
        f'<textarea rows="5" style="width:100%;" readonly>{invite_url}</textarea>'
        '<p><a href="/syuwa/admin/invites">招待管理へ戻る</a></p>'
    )


@syuwa_bp.route("/apply", methods=["GET"])
def syuwa_apply():
    token = request.args.get("token", "")

    if not verify_syuwa_invite(token):
        abort(403)

    return render_template("syuwa_apply.html")
