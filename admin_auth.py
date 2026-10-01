import os
kuri_login_attempts = {}

from functools import wraps
from flask import request, Response
from datetime import datetime, timedelta


def admin_required(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")

        auth = request.authorization

        if (
            not auth
            or auth.username != username
            or auth.password != password
        ):
            return Response(
                """
                <div style="font-size:32px; text-align:center; margin-top:80px;">
                    認証がキャンセルされました。<br><br>
                    画面を閉じてください。
                </div>
                """,
                401,
                {
                    "WWW-Authenticate":
                    'Basic realm="unei-yomitori"'
                }
            )

        return func(*args, **kwargs)

    return decorated

def qr_required(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        username = os.environ.get("QRcode_USERNAME")
        password = os.environ.get("QRcode_PASSWORD")

        auth = request.authorization

        if (
            not auth
            or auth.username != username
            or auth.password != password
        ):
            return Response(
                """
                <div style="font-size:32px; text-align:center; margin-top:80px;">
                    認証がキャンセルされました。<br><br>
                    画面を閉じてください。
                </div>
                """,
                401,
                {
                    "WWW-Authenticate":
                    'Basic realm="QRcode"'
                }
            )

        return func(*args, **kwargs)

    return decorated


def member_required(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        username = os.environ.get("kuri_USERNAME")
        password = os.environ.get("kuri_PASSWORD")

        ip = request.remote_addr
        now = datetime.now()

        attempt = kuri_login_attempts.get(ip)

        if attempt and attempt["locked_until"]:
            if now < attempt["locked_until"]:
                return Response(
                    "ログイン試行回数を超えました。30分後に再度お試しください。",
                    403
                )
            else:
                kuri_login_attempts.pop(ip, None)

        auth = request.authorization

        if (
            not auth
            or auth.username != username
            or auth.password != password
        ):
            attempt = kuri_login_attempts.get(
                ip,
                {"count": 0, "locked_until": None}
            )

            attempt["count"] += 1

            if attempt["count"] >= 3:
                attempt["locked_until"] = now + timedelta(minutes=30)

            kuri_login_attempts[ip] = attempt                

            
            return Response(
                """
                <div style="font-size:32px; text-align:center; margin-top:80px;">
                    認証がキャンセルされました。<br><br>
                    画面を閉じてください。
                </div>
                """,
                401,
                {
                    "WWW-Authenticate":
                    'Basic realm="member-video"'
                }
            )

        kuri_login_attempts.pop(ip, None)

        return func(*args, **kwargs)

    return decorated
