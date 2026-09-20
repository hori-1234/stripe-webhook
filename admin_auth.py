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
                "管理者認証が必要です",
                401,
                {
                    "WWW-Authenticate":
                    'Basic realm="Admin"'
                }
            )

        return func(*args, **kwargs)

    return decorated
