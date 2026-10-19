from flask import Blueprint, session
from event_schedule.memo_auth import is_memo_logged_in

oshikatsu_bp = Blueprint(
    "oshikatsu",
    __name__,
    url_prefix="/oshikatsu"
)

oshikatsu_bp = Blueprint(
    "oshikatsu",
    __name__,
    url_prefix="/oshikatsu"
)


@oshikatsu_bp.route("/")
def oshikatsu_home():
    if not is_memo_logged_in():
        return "推し活日記：未ログイン"

    user_id = session.get("memo_user_id")

    return f"推し活日記：ログイン中（ユーザーID：{user_id}）"
