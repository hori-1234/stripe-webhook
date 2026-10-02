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

    register_message = ""
    edit_message = ""
    delete_message = ""
    current_search_words = ""
    edit_url_value = ""

    if request.method == "POST" and request.form.get("action") == "register":
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
                register_message = "この動画は登録済みです。"
            else:
                cur.execute(
                    """
                    INSERT INTO member_videos (search_words, x_url)
                    VALUES (%s, %s)
                    """,
                    (search_words, x_url)
                )

                conn.commit()
                register_message = "動画を登録しました。"

            cur.close()
            conn.close()


    if request.method == "POST" and request.form.get("action") == "load_edit":
        edit_url_value = request.form.get("edit_url", "").strip()

        if edit_url_value:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute(
                """
                SELECT search_words
                FROM member_videos
                WHERE x_url = %s
                """,
                (edit_url_value,)
            )

            row = cur.fetchone()

            cur.close()
            conn.close()

            if row:
                current_search_words = row[0]
            else:
                edit_message = "該当する動画は登録されていません."

    if request.method == "POST" and request.form.get("action") == "edit":
        edit_url = request.form.get("edit_url", "").strip()
        new_search_words = request.form.get("new_search_words", "").strip()

        if edit_url and new_search_words:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE member_videos
                SET search_words = %s
                WHERE x_url = %s
                """,
                (new_search_words, edit_url)
            )

            updated_count = cur.rowcount
            conn.commit()

            cur.close()
            conn.close()

            if updated_count > 0:
                edit_message = "検索ワードを修正しました。"
            else:
                edit_message = "該当する動画は登録されていません。"

    if request.method == "POST" and request.form.get("action") == "delete":
        delete_url = request.form.get("delete_url", "").strip()

        if delete_url:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute(
                """
                DELETE FROM member_videos
                WHERE x_url = %s
                """,
                (delete_url,)
            )

            deleted_count = cur.rowcount
            conn.commit()

            cur.close()
            conn.close()

            if deleted_count > 0:
                delete_message = "動画を削除しました。"
            else:
                delete_message = "該当する動画は登録されていません。"

    return render_template_string("""
        <h1>動画登録</h1>

        <h2>登録</h2>
    
        <form method="POST">
            <input type="hidden" name="action" value="register">
        
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

        {% if register_message %}
            <p style="font-size:24px; font-weight:bold;">
                {{ register_message }}
            </p>
        {% endif %}

        <hr style="margin-top:40px; margin-bottom:40px;">

        <h2>検索ワード修正</h2>

        <form method="POST">
            <input type="hidden" name="action" value="load_edit">

            <p>修正する動画のリンク</p>

            <input
                type="text"
                name="edit_url"
                value="{{ edit_url_value }}"
                placeholder="https://x.com/..."
                required
                style="width:400px; padding:12px; font-size:18px;"
            >

            <br><br>

            <button
                type="submit"
                style="padding:12px 24px; font-size:18px;"
            >
                現在のワードを表示
            </button>
        </form>

        {% if current_search_words %}

            <form method="POST" style="margin-top:20px;">
                <input type="hidden" name="action" value="edit">
                <input type="hidden" name="edit_url" value="{{ edit_url_value }}">

                <p>検索ワード</p>

                <input
                    type="text"
                    name="new_search_words"
                    value="{{ current_search_words }}"
                    required
                    style="width:400px; padding:12px; font-size:18px;"
                >

                <br><br>

                <button
                    type="submit"
                    style="padding:12px 24px; font-size:18px;"
                >
                    修正
                </button>

                <button
                    type="button"
                    onclick="window.location.href='/admin/member-video/register'"
                    style="padding:12px 24px; font-size:18px; margin-left:10px;"
                >
                    キャンセル
                </button>

            </form>

        {% endif %}

        {% if edit_message %}
            <p style="font-size:24px; font-weight:bold;">
                {{ edit_message }}
            </p>
        {% endif %}

                <hr style="margin-top:40px; margin-bottom:40px;">

        <h2>削除</h2>

        <form method="POST">
            <input type="hidden" name="action" value="delete">

            <p>削除する動画のリンク</p>
            <input
                type="text"
                name="delete_url"
                placeholder="https://x.com/..."
                required
                style="width:400px; padding:12px; font-size:18px;"
            >

            <br><br>

            <button
                type="submit"
                style="padding:12px 24px; font-size:18px;"
            >
                削除
            </button>
        </form>

        {% if delete_message %}
            <p style="font-size:24px; font-weight:bold;">
                {{ delete_message }}
            </p>
        {% endif %}

    """,
    register_message=register_message,
    edit_message=edit_message,
    delete_message=delete_message,
    current_search_words=current_search_words,
    edit_url_value=edit_url_value
    )
    
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

    create_video_table()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT search_words
        FROM member_videos
    """)

    word_rows = cur.fetchall()

    words = set()

    for row in word_rows:
        for word in row[0].split():
            words.add(word)

    word_list = sorted(words)
    kana_groups = {
        "あ行": "あいうえおアイウエオ",
        "か行": "かきくけこがぎぐげごカキクケコガギグゲゴ",
        "さ行": "さしすせそざじずぜぞサシスセソザジズゼゾ",
        "た行": "たちつてとだぢづでどタチツテトダヂヅデド",
        "な行": "なにぬねのナニヌネノ",
        "は行": "はひふへほばびぶべぼぱぴぷぺぽハヒフヘホバビブベボパピプペポ",
        "ま行": "まみむめもマミムメモ",
        "や行": "やゆよヤユヨ",
        "ら行": "らりるれろラリルレロ",
        "わ行": "わをんワヲン",
        "英数字・その他": ""
    }

    grouped_words = {group: [] for group in kana_groups}

    for word in word_list:
        first = word[0]

        found = False

        for group, chars in kana_groups.items():
            if first in chars:
                grouped_words[group].append(word)
                found = True
                break

        if not found:
            grouped_words["英数字・その他"].append(word)    

    cur.close()
    conn.close()
    
    if performer:

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

        .word-list {
            position: fixed;
            top: 30px;
            right: 30px;
            width: 250px;
            max-height: 85vh;
            overflow-y: auto;
            border: 1px solid #ccc;
            padding: 15px;
            background: white;
        }

        .word-list a {
            display: inline-block;
            padding: 5px 0;
            font-size: 18px;
        }

        @media (max-width: 700px) {
            .word-list {
                position: static;
                width: auto;
                max-height: 300px;
                margin-top: 30px;
            }
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

<div class="word-list">
    <h2>登録ワード一覧</h2>

    {% for group, words in grouped_words.items() %}

        {% if words %}
            <h3>{{ group }}</h3>

            {% for word in words %}
                <a href="/member-video?performer={{ word }}">
                    {{ word }}
                </a><br>
            {% endfor %}
        {% endif %}

    {% endfor %}
</div>

<hr>

<h2>検索結果</h2>

{% if performer %}
    <p>「{{ performer }}」の動画</p>
{% endif %}

{% for video in results %}
    <p>
        {{ loop.index }}.
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
""",
performer=performer,
results=results,
word_list=word_list,
grouped_words=grouped_words
)
