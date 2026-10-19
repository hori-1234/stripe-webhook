from flask import render_template_string


def render_nikki_form(logged_in, csrf_token=""):
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>推し活日記</title>
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

        <p>日付</p>
        <input type="date" name="event_date" required>

        <p>イベント名</p>
        <input type="text" name="event_name">

        <p>場所</p>
        <input type="text" name="place">

        <p>出演者</p>
        <textarea name="performers"></textarea>

        <p>日記</p>
        <textarea name="diary_text"></textarea>

        {% if logged_in %}
            <p><button type="submit">保存</button></p>
        {% endif %}
    </form>

    <p><a href="/schedule">イベスケに戻る</a></p>
</body>
</html>
    """, logged_in=logged_in, csrf_token=csrf_token)
