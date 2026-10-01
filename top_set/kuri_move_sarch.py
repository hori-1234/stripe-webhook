import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template_string, request, session, redirect, url_for

kuri_move_sarch_bp = Blueprint("kuri_move_sarch", __name__)
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 3
LOCK_MINUTES = 30
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
            return "ログイン試行回数を超えました。30分間ログインできません。", 403
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
            return "ログイン試行回数を超えました。30分間ログインできません。", 403

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

    videos = []

    results = []

    if performer:
        for video in videos:
            if performer.lower() in video["performers"].lower():
                results.append(video)
  
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

