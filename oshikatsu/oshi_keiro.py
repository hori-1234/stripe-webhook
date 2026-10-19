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
    import secrets
    from flask import render_template_string

    logged_in = is_memo_logged_in()

    if logged_in and not session.get("oshi_csrf_token"):
        session["oshi_csrf_token"] = secrets.token_urlsafe(32)

    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>推し活日記</title>
    <style>
        body {
            font-family: sans-serif;
            max-width: 700px;
            margin: 30px auto;
            padding: 0 15px;
        }
        label {
            display: block;
            margin-top: 18px;
            font-weight: bold;
        }
        input, textarea {
            width: 100%;
            box-sizing: border-box;
            padding: 10px;
            margin-top: 5px;
            font-size: 16px;
        }
        textarea {
            min-height: 180px;
        }
        button {
            margin-top: 20px;
            padding: 12px 30px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h2>推し活日記</h2>

    {% if logged_in %}
        <p>ログイン中</p>
    {% else %}
        <p>未ログイン：入力内容は保存できません。</p>
        <a href="/schedule/login">ログイン</a>
    {% endif %}

    <form method="POST" action="/oshikatsu/save">
        {% if logged_in %}
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        {% endif %}

        <label for="event_date">日付</label>
        <input type="date" id="event_date" name="event_date" required>

        <label for="event_name">イベント名</label>
        <input type="text" id="event_name" name="event_name">

        <label for="place">場所</label>
        <input type="text" id="place" name="place">

        <label for="performers">出演者</label>
        <textarea id="performers" name="performers" rows="3"></textarea>

        <label for="diary_text">日記</label>
        <textarea id="diary_text" name="diary_text"></textarea>

        {% if logged_in %}
            <button type="submit">保存</button>
        {% endif %}
    </form>

    <p><a href="/schedule">イベスケに戻る</a></p>
</body>
</html>
    """,
        logged_in=logged_in,
        csrf_token=session.get("oshi_csrf_token", "")
    )


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
