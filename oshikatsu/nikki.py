from flask import render_template_string
from oshikatsu.nikki_photo import render_nikki_photo_form
from oshikatsu.nikki_layout import render_nikki_layout


def render_nikki_form(logged_in, csrf_token=""):
    photo_form = render_nikki_photo_form()
    diary_layout = render_nikki_layout(mode="input")
    
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

    <form method="POST" action="/oshikatsu/save" enctype="multipart/form-data">
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

        {{ photo_form }}

        {% if logged_in %}
            <p><button type="submit">保存</button></p>
        {% endif %}
    </form>

    <p><a href="/schedule">イベスケに戻る</a></p>
</body>
</html>
    """, logged_in=logged_in, csrf_token=csrf_token, photo_form=photo_form)


def render_nikki_view(diary):
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>推し活日記 - 閲覧</title>
</head>
<body>
    <h2>推し活日記</h2>

    <p><strong>日付：</strong>{{ diary[0] }}</p>

    <p><strong>イベント名：</strong>{{ diary[1] }}</p>

    <p><strong>場所：</strong>{{ diary[2] }}</p>

    <p><strong>出演者：</strong>{{ diary[3] }}</p>

    <p><strong>日記：</strong></p>
    <p style="white-space: pre-wrap;">{{ diary[4] }}</p>

    <p><a href="/oshikatsu/">戻る</a></p>
</body>
</html>
    """, diary=diary)
