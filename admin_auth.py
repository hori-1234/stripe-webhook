import os
from functools import wraps
from flask import request, Response


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
