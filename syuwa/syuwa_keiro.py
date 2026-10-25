import os
import hmac
import re
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


@syuwa_bp.route("/apply", methods=["GET", "POST"])
def syuwa_apply():

    if request.method == "POST":
        token = request.form.get("token", "")
        submitted_csrf = request.form.get("csrf_token", "")
        expected_csrf = session.get("syuwa_apply_csrf_token", "")

        if not expected_csrf:
            abort(403)

        if not hmac.compare_digest(submitted_csrf, expected_csrf):
            abort(403)

        if not verify_syuwa_invite(token):
            abort(403)

        applicant_name = request.form.get("applicant_name", "").strip()
        email = request.form.get("email", "").strip()
        comment = request.form.get("comment", "").strip()

        if not applicant_name or len(applicant_name) > 100:
            abort(400)

        if (
            not email
            or len(email) > 255
            or "@" not in email
        ):
            abort(400)

        if len(comment) > 2000:
            abort(400)

        from syuwa.syuwa_db import save_syuwa_application
        from psycopg2.errors import UniqueViolation

        try:
            saved = save_syuwa_application(
                token,
                applicant_name,
                email,
                comment
            )
        except UniqueViolation as e:
            if e.diag.constraint_name != "syuwa_applications_applicant_name_unique":
                raise

            return render_template(
                "syuwa_apply.html",
                invite_token=token,
                csrf_token=expected_csrf,
                error="このIDは既に使用されています。別のIDを入力してください。",
                applicant_name=applicant_name,
                email=email,
                comment=comment
            ), 409

        if not saved:
            abort(403)


        session.pop("syuwa_apply_csrf_token", None)

        return """
        <h2>登録者申請を受け付けました</h2>
        <p>管理者による承認をお待ちください。</p>
        """

    token = request.args.get("token", "")

    if not verify_syuwa_invite(token):
        abort(403)

    csrf_token = secrets.token_urlsafe(32)
    session["syuwa_apply_csrf_token"] = csrf_token

    return render_template(
        "syuwa_apply.html",
        invite_token=token,
        csrf_token=csrf_token
    )


@syuwa_bp.route("/admin/applications", methods=["GET"])
@admin_required
def syuwa_admin_applications():
    from syuwa.syuwa_db import get_syuwa_applications
    from flask import render_template_string
    from markupsafe import Markup, escape

    if "syuwa_admin_application_csrf" not in session:
        session["syuwa_admin_application_csrf"] = secrets.token_urlsafe(32)

    csrf_token = session["syuwa_admin_application_csrf"]

    applications = get_syuwa_applications()

    rows = ""

    for application in applications:
        application_id, name, email, comment, status, created_at, password_set = application

        status_labels = {
            "pending": "未対応",
            "approved": "登録完了" if password_set else "承認済み",
            "rejected": "却下",
            "disabled": "無効化"
        }

        status_text = status_labels.get(status, status)


        if status == "pending":
            status_html = f"""
                <form method="POST" action="/syuwa/admin/applications/update">
                    <input type="hidden" name="csrf_token" value="{csrf_token}">
                    <input type="hidden" name="application_id" value="{application_id}">

                    <button type="submit" name="status" value="approved">
                        承認
                    </button>

                    <button type="submit" name="status" value="rejected"
                            onclick="return confirm('この申請を却下しますか？');">
                        却下
                    </button>
                </form>
            """
       
        elif status == "approved":
            if password_set:
                action_url = "/syuwa/admin/password-reset/create"
                button_text = "パスワード再設定URL発行"
            else:
                action_url = "/syuwa/admin/password-token/create"
                button_text = "パスワード設定URL発行"

            status_html = f"""
                <form method="POST" action="{action_url}">
                    <input type="hidden" name="csrf_token" value="{csrf_token}">
                    <input type="hidden" name="application_id" value="{application_id}">

                    <button type="submit">
                        {button_text}
                    </button>
                </form>
            """

            if password_set:
                status_html += f"""
                    <form method="POST" action="/syuwa/admin/account/update">
                        <input type="hidden" name="csrf_token" value="{csrf_token}">
                        <input type="hidden" name="application_id" value="{application_id}">
                        <input type="hidden" name="action" value="disable">

                        <button type="submit"
                                onclick="return confirm('このアカウントを無効化しますか？');">
                            無効化
                        </button>
                    </form>
                """

        elif status == "disabled":
            status_html = f"""
                <form method="POST" action="/syuwa/admin/account/update">
                    <input type="hidden" name="csrf_token" value="{csrf_token}">
                    <input type="hidden" name="application_id" value="{application_id}">
                    <input type="hidden" name="action" value="enable">

                    <button type="submit">有効化</button>
                </form>
            """

        else:
            status_html = ""

        rows += f"""

        <tr>
            <td>{application_id}</td>
            <td>{escape(name)}</td>
            <td>{escape(email)}</td>
            <td>{escape(comment or "")}</td>
            <td>{escape(status_text)}{status_html}</td>
            <td>{created_at.strftime('%Y/%m/%d %H:%M')}</td>
        </tr>
        """

    if not rows:
        rows = '<tr><td colspan="6">申請はありません</td></tr>'

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>手話アプリ 登録者申請一覧</title>
        <style>
            body {
                font-family: sans-serif;
                padding: 20px;
                background: #f5f7fa;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
            }

            th, td {
                border: 1px solid #ccc;
                padding: 10px;
                text-align: left;
                overflow-wrap: anywhere;
            }

            th {
                background: #1769aa;
                color: white;
            }

            .table-wrap {
                overflow-x: auto;
            }
        </style>
    </head>
    <body>
        <h2>登録者申請一覧</h2>

        <p><a href="/syuwa/admin/invites">招待管理へ戻る</a></p>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>ID</th>
                    <th>登録者ID名</th>
                    <th>メールアドレス</th>
                    <th>コメント</th>
                    <th>状態</th>
                    <th>申請日時</th>
                </tr>
                {{ rows }}
            </table>
        </div>
    </body>
    </html>
    """, rows=Markup(rows))


@syuwa_bp.route("/admin/applications/update", methods=["POST"])
@admin_required
def syuwa_update_application():
    from syuwa.syuwa_db import update_syuwa_application_status

    submitted_csrf = request.form.get("csrf_token", "")
    expected_csrf = session.get("syuwa_admin_application_csrf", "")

    if not expected_csrf:
        abort(403)

    if not hmac.compare_digest(submitted_csrf, expected_csrf):
        abort(403)

    application_id = request.form.get("application_id", "")
    status = request.form.get("status", "")

    if not application_id.isdigit():
        abort(400)

    if status not in ("approved", "rejected"):
        abort(400)

    updated = update_syuwa_application_status(
        int(application_id),
        status
    )

    if not updated:
        abort(409)

    if status == "approved":
        from syuwa.syuwa_db import (
            get_syuwa_approved_applicant,
            create_syuwa_password_token
        )
        from syuwa.syuwa_mail import send_syuwa_approval_email

        applicant = get_syuwa_approved_applicant(int(application_id))

        if applicant is None:
            abort(409)

        applicant_name, email = applicant

        token = create_syuwa_password_token(int(application_id))

        if token is None:
            abort(409)

        password_url = (
            request.url_root.rstrip("/")
            + "/syuwa/password/setup?token="
            + token
        )

        try:
            send_syuwa_approval_email(
                email,
                applicant_name,
                password_url
            )
        except Exception:
            abort(502, description="承認済みですが、メール送信に失敗しました。再送信が必要です。")

    from flask import redirect, url_for

    return redirect(
        url_for("syuwa.syuwa_admin_applications"),
        code=303
    )


@syuwa_bp.route("/admin/account/update", methods=["POST"])
@admin_required
def syuwa_admin_account_update():
    from flask import redirect, url_for
    from syuwa.syuwa_db import update_syuwa_account_enabled

    submitted_csrf = request.form.get("csrf_token", "")
    expected_csrf = session.get("syuwa_admin_application_csrf", "")

    if not expected_csrf:
        abort(403)

    if not hmac.compare_digest(submitted_csrf, expected_csrf):
        abort(403)

    application_id = request.form.get("application_id", "")
    action = request.form.get("action", "")

    if not application_id.isdigit():
        abort(400)

    if action == "enable":
        enabled = True
    elif action == "disable":
        enabled = False
    else:
        abort(400)

    updated = update_syuwa_account_enabled(
        int(application_id),
        enabled
    )

    if not updated:
        abort(409)

    return redirect(
        url_for("syuwa.syuwa_admin_applications"),
        code=303
    )


@syuwa_bp.route("/admin/password-token/create", methods=["POST"])
@admin_required
def syuwa_create_password_token():
    from syuwa.syuwa_db import create_syuwa_password_token
    from flask import url_for
    from markupsafe import escape

    submitted_csrf = request.form.get("csrf_token", "")
    expected_csrf = session.get("syuwa_admin_application_csrf", "")

    if not expected_csrf:
        abort(403)

    if not hmac.compare_digest(submitted_csrf, expected_csrf):
        abort(403)

    application_id = request.form.get("application_id", "")

    if not application_id.isdigit():
        abort(400)

    from syuwa.syuwa_db import get_syuwa_approved_applicant
    from syuwa.syuwa_mail import send_syuwa_approval_email
    from flask import redirect

    applicant = get_syuwa_approved_applicant(int(application_id))

    if applicant is None:
        abort(409)

    applicant_name, email = applicant

    token = create_syuwa_password_token(int(application_id))

    if token is None:
        abort(409)

    password_url = (
        request.url_root.rstrip("/")
        + url_for("syuwa.syuwa_password_setup")
        + "?token="
        + token
    )

    try:
        send_syuwa_approval_email(
            email,
            applicant_name,
            password_url
        )
    except Exception:
        abort(
            502,
            description="メール送信に失敗しました。再度お試しください。"
        )

    return redirect(
        url_for("syuwa.syuwa_admin_applications"),
        code=303
    )


@syuwa_bp.route("/admin/password-reset/create", methods=["POST"])
@admin_required
def syuwa_create_password_reset():
    from syuwa.syuwa_db import (
        get_syuwa_password_reset_applicant,
        create_syuwa_password_reset_token
    )
    from flask import redirect, url_for

    submitted_csrf = request.form.get("csrf_token", "")
    expected_csrf = session.get("syuwa_admin_application_csrf", "")

    if not expected_csrf:
        abort(403)

    if not hmac.compare_digest(submitted_csrf, expected_csrf):
        abort(403)

    application_id = request.form.get("application_id", "")

    if not application_id.isdigit():
        abort(400)

    applicant = get_syuwa_password_reset_applicant(
        int(application_id)
    )

    if applicant is None:
        abort(409)

    applicant_name, email = applicant

    token = create_syuwa_password_reset_token(
        int(application_id)
    )

    if token is None:
        abort(409)

    password_url = (
        request.url_root.rstrip("/")
        + url_for("syuwa.syuwa_password_reset")
        + "?token="
        + token
    )

    from syuwa.syuwa_mail import send_syuwa_password_reset_email

    try:
        send_syuwa_password_reset_email(
            email,
            applicant_name,
            password_url
        )
    except Exception:
        abort(
            502,
            description="再設定メールの送信に失敗しました。再度お試しください。"
        )

    return redirect(
        url_for("syuwa.syuwa_admin_applications"),
        code=303
    )


@syuwa_bp.route("/password/setup", methods=["GET", "POST"])
def syuwa_password_setup():

    from syuwa.syuwa_db import (
        verify_syuwa_password_token,
        complete_syuwa_password_setup
    )

    if request.method == "POST":
        token = request.form.get("token", "")
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        submitted_csrf = request.form.get("csrf_token", "")
        expected_csrf = session.get("syuwa_password_setup_csrf", "")

        if not expected_csrf:
            abort(403)

        if not hmac.compare_digest(submitted_csrf, expected_csrf):
            abort(403)

        if password != password_confirm:
            abort(400, description="パスワードが一致しません")

        if not re.fullmatch(r"[A-Za-z0-9]{6}", password):
            abort(400, description="パスワードは6桁の半角英数字にしてください")

        if not complete_syuwa_password_setup(token, password):
            abort(403)

        session.pop("syuwa_password_setup_csrf", None)

        return """
        <h2>パスワード設定が完了しました</h2>
        <p>ログイン機能の準備ができるまでお待ちください。</p>
        """

    token = request.args.get("token", "")

    if not verify_syuwa_password_token(token):
        abort(403)

    csrf_token = secrets.token_urlsafe(32)
    session["syuwa_password_setup_csrf"] = csrf_token

    return render_template(
        "syuwa_password_setup.html",
        token=token,
        csrf_token=csrf_token
    )


@syuwa_bp.route("/password/reset", methods=["GET", "POST"])
def syuwa_password_reset():
    from syuwa.syuwa_db import (
        verify_syuwa_password_reset_token,
        complete_syuwa_password_reset
    )

    if request.method == "POST":
        token = request.form.get("token", "")
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        submitted_csrf = request.form.get("csrf_token", "")
        expected_csrf = session.get("syuwa_password_reset_csrf", "")

        if not expected_csrf:
            abort(403)

        if not hmac.compare_digest(submitted_csrf, expected_csrf):
            abort(403)

        if password != password_confirm:
            abort(400, description="パスワードが一致しません")

        if not re.fullmatch(r"[A-Za-z0-9]{6}", password):
            abort(400, description="パスワードは6桁の半角英数字にしてください")

        if not complete_syuwa_password_reset(token, password):
            abort(403)

        session.pop("syuwa_password_reset_csrf", None)

        return """
        <h2>パスワードの再設定が完了しました</h2>
        <p><a href="/syuwa/login">ログイン画面へ</a></p>
        """

    token = request.args.get("token", "")

    if not verify_syuwa_password_reset_token(token):
        abort(403)

    csrf_token = secrets.token_urlsafe(32)
    session["syuwa_password_reset_csrf"] = csrf_token

    return render_template(
        "syuwa_password_reset.html",
        token=token,
        csrf_token=csrf_token
    )


@syuwa_bp.route("/login", methods=["GET", "POST"])
def syuwa_login():

    from flask import redirect, url_for

    if request.method == "POST":
        from syuwa.syuwa_db import authenticate_syuwa_user

        submitted_csrf = request.form.get("csrf_token", "")
        expected_csrf = session.get("syuwa_login_csrf", "")

        if not expected_csrf:
            abort(403)

        if not hmac.compare_digest(submitted_csrf, expected_csrf):
            abort(403)

        applicant_name = request.form.get("applicant_name", "").strip()
        password = request.form.get("password", "")

        if not applicant_name or not password:
            abort(400)
        
        user_id = authenticate_syuwa_user(applicant_name, password)

        if user_id is None:
            from syuwa.syuwa_db import is_syuwa_account_disabled

            if is_syuwa_account_disabled(applicant_name, password):
                error_message = "※ログイン権限がありません"
            else:
                error_message = "※登録者ID名またはパスワードが違います"

            csrf_token = secrets.token_urlsafe(32)
            session["syuwa_login_csrf"] = csrf_token

            return render_template(
                "syuwa_login.html",
                csrf_token=csrf_token,
                error=error_message
            ), 401

        session.pop("syuwa_user_id", None)
        session.pop("syuwa_login_csrf", None)
        session.permanent = True
        session["syuwa_user_id"] = user_id

        return redirect(url_for("syuwa.syuwa_login_complete"), code=303)

    csrf_token = secrets.token_urlsafe(32)
    session["syuwa_login_csrf"] = csrf_token

    return render_template(
        "syuwa_login.html",
        csrf_token=csrf_token
    )


@syuwa_bp.route("/login/complete", methods=["GET"])
def syuwa_login_complete():
    from flask import redirect, url_for
    from markupsafe import escape

    user_id = session.get("syuwa_user_id")

    if user_id is None:
        return redirect(url_for("syuwa.syuwa_login"), code=303)

    from syuwa.syuwa_db import is_syuwa_user_active

    if not is_syuwa_user_active(user_id):
        session.pop("syuwa_user_id", None)
        session.pop("syuwa_logout_csrf", None)

        return redirect(
            url_for("syuwa.syuwa_login"),
            code=303
        )

    csrf_token = secrets.token_urlsafe(32)
    session["syuwa_logout_csrf"] = csrf_token

    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>手話アプリ ログイン完了</title>
    </head>
    <body>
        <h2>ログインしました</h2>
        <p>動画登録機能は現在準備中です。</p>

        <form method="POST" action="/syuwa/logout">
            <input type="hidden" name="csrf_token" value="{csrf_token}">
            <button type="submit">ログアウト</button>
        </form>
    </body>
    </html>
    """.replace("{csrf_token}", csrf_token)


@syuwa_bp.route("/logout", methods=["POST"])
def syuwa_logout():
    from flask import redirect, url_for

    submitted_csrf = request.form.get("csrf_token", "")
    expected_csrf = session.get("syuwa_logout_csrf", "")

    if not expected_csrf:
        abort(403)

    if not hmac.compare_digest(submitted_csrf, expected_csrf):
        abort(403)

    session.pop("syuwa_user_id", None)
    session.pop("syuwa_logout_csrf", None)

    return redirect(
        url_for("syuwa.syuwa_login"),
        code=303
    )
