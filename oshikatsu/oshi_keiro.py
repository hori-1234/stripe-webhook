import os
import psycopg2

from flask import Blueprint, session
from event_schedule.memo_auth import is_memo_logged_in

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


@oshikatsu_bp.route("/save", methods=["POST"])
def save_oshi_diary():
    if not is_memo_logged_in():
        return "ログインが必要です", 401

    import secrets
    from flask import request

    csrf_token = request.form.get("csrf_token", "")
    expected_token = session.get("oshi_csrf_token", "")

    if (
        not csrf_token
        or not expected_token
        or not secrets.compare_digest(csrf_token, expected_token)
    ):
        return "不正なリクエストです", 403

    user_id = session.get("memo_user_id")

    return f"保存処理の接続成功（ユーザーID：{user_id}）"
