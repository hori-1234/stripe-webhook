import os
import requests
import psycopg2
from datetime import datetime, timedelta
from flask import Blueprint, render_template_string, request, session, redirect, url_for
from admin_auth import admin_required

kuri_move_sarch_bp = Blueprint("kuri_move_sarch", __name__)

X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

login_attempts = {}
MAX_LOGIN_ATTEMPTS = 3
LOCK_MINUTES = 30

def create_video_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS member_videos (
            id SERIAL PRIMARY KEY,
            search_words TEXT NOT NULL,
            x_url TEXT NOT NULL UNIQUE,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

@kuri_move_sarch_bp.route("/admin/member-video/register", methods=["GET", "POST"])
@admin_required
def register_video():
    create_video_table()

    message = ""

    if request.method == "POST":
        search_words = request.form.get("search_words", "").strip()
        x_url = request.form.get("x_url", "").strip()

        if search_words and x_url:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute(
                """
                SELECT id
                FROM member_videos
                WHERE x_url = %s
                """,
                (x_url,)
            )

            existing_video = cur.fetchone()

            if existing_video:
                message = "この動画は登録済みです。"
            else:
                cur.execute(
                    """
                    INSERT INTO member_videos (search_words, x_url)
                    VALUES (%s, %s)
                    """,
                    (search_words, x_url)
                )

                conn.commit()
                message = "動画を登録しました。"

            cur.close()
            conn.close()

    return render_template_string("""
        <h1>動画登録</h1>

        <form method="POST">
            <p>検索ワード</p>
            <input
                type="text"
                name="search_words"
                placeholder="例：グループ名　活動者名A　活動者B"
                required
                style="width:400px; padding:12px; font-size:18px;"
            >
            <p>※グループ名・活動者名はスペースで区切って入力してください。</p>

            <p>リンク</p>
            <input
                type="text"
                name="x_url"
                placeholder="https://x.com/..."
                required
                style="width:400px; padding:12px; font-size:18px;"
            >

            <br><br>

            <button
                type="submit"
                style="padding:12px 24px; font-size:18px;"
            >
                登録
            </button>
        </form>

        {% if message %}
            <p style="font-size:24px; font-weight:bold;">
                {{ message }}
            </p>
        {% endif %}

    """, message=message)

@kuri_move_sarch_bp.route("/member-video/x-test")
def x_test():
    headers = {
        "Authorization": f"Bearer {X_ACCESS_TOKEN}"
    }

    response = requests.get(
        "https://api.x.com/2/users/1870989834912985088/tweets",
        headers=headers,
        params={
            "max_results": 10
        }
    )

    return {
        "status": response.status_code,
        "body": response.json()
    }


@kuri_move_sarch_bp.route("/member-video/login", methods=["GET", "POST"])

def member_login():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ip = ip.split(",")[0].strip()
    attempt = login_attempts.get(
        ip,
        {"count": 0, "locked_until": None}
    )

    locked_until = attempt.get("locked_until")

    if locked_until:
        if datetime.now() < locked_until:
            return """
            <div style="font-size:32px; text-align:center; margin-top:80px;">
                ログイン試行回数を超えました。<br>
                30分間ログインできません。
            </div>
            """, 403
        else:
            login_attempts.pop(ip, None)
            attempt = {"count": 0, "locked_until": None}
            
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        correct_username = os.environ.get("kuri_USERNAME")
        correct_password = os.environ.get("kuri_PASSWORD")
        
        if username == correct_username and password == correct_password:
            login_attempts.pop(ip, None)
            session["member_logged_in"] = True
            return redirect(url_for("kuri_move_sarch.member_video"))

        attempt["count"] += 1

        if attempt["count"] >= MAX_LOGIN_ATTEMPTS:
            attempt["locked_until"] = datetime.now() + timedelta(minutes=LOCK_MINUTES)

        login_attempts[ip] = attempt

        if attempt["count"] >= MAX_LOGIN_ATTEMPTS:
            return """
            <div style="font-size:32px; text-align:center; margin-top:80px;">
                ログイン試行回数を超えました。<br>
                30分間ログインできません。
            </div>
            """, 403

    remaining = MAX_LOGIN_ATTEMPTS - attempt["count"]

    return render_template_string("""
        
        <h1>クリサポログイン</h1>

        {% if remaining < 3 %}
            <p>ログイン失敗：残り {{ remaining }} 回</p>
        {% endif %}

        <form method="POST">
            <input
                type="text"
                name="username"
                placeholder="ユーザー名"
                required
                style="width:300px; padding:12px; font-size:18px;"
            >
            <br><br>

            <input
                type="password"
                name="password"
                placeholder="パスワード"
                required
                style="width:300px; padding:12px; font-size:18px;"
            >
            <br><br>

            <button
                type="submit"
                style="padding:12px 24px; font-size:18px;"
            >
                ログイン
            </button>
        </form>

    """, remaining=remaining)

@kuri_move_sarch_bp.route("/member-video")
def member_video():
    if not session.get("member_logged_in"):
        return redirect(url_for("kuri_move_sarch.member_login"))

    performer = request.args.get("performer", "").strip()
    results = []

    if performer:
        create_video_table()

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT search_words, x_url
            FROM member_videos
            WHERE search_words ILIKE %s
            ORDER BY created_at DESC
            """,
            (f"%{performer}%",)
        )

        rows = cur.fetchall()

        cur.close()
        conn.close()

        for row in rows:
            results.append({
                "performers": row[0],
                "url": row[1]
            })

    return render_template_string("""

<!DOCTYPE html>
<html lang="ja">
<head>
    <style>
        input[type="text"] {
            width: 300px;
            padding: 12px;
            font-size: 18px;
        }

        button {
            padding: 12px 24px;
            font-size: 18px;
        }
    </style>

    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>動画検索</title>
</head>

<body>

    <h1>動画検索</h1>

    <form method="GET" action="/member-video">
    <input
        type="text"
        name="performer"
        placeholder="出演者名を入力"
    >

    <button type="submit">
        検索
    </button>
    
</form>

<hr>

<h2>検索結果</h2>

{% if performer %}
    <p>「{{ performer }}」の動画</p>
{% endif %}

{% for video in results %}
    <p>
        <a href="{{ video['url'] }}" target="_blank">
            Xで動画を見る
        </a>
    </p>
{% endfor %}

{% if performer and not results %}
    <p>該当する動画はありません。</p>
{% endif %}

</body>
</html>
""", performer=performer, results=results)

