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

        {{ diary_layout }}
        
        {{ photo_form }}

        {% if logged_in %}
            <p><button type="submit">保存</button></p>
        {% endif %}
    </form>

    <p><a href="/schedule">イベスケに戻る</a></p>
</body>
</html>
    """, logged_in=logged_in, csrf_token=csrf_token, photo_form=photo_form, diary_layout=diary_layout)


def render_nikki_view(diary, photo_view="", diary_id=None):
    diary_layout = render_nikki_layout(
        diary=diary,
        mode="view"
    )

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

    {{ diary_layout }}

    {{ photo_view }}

    <p>
        <a href="/oshikatsu/edit/{{ diary_id }}">編集</a>
    </p>

    <p><a href="/oshikatsu/">戻る</a></p>
</body>
</html>
    """,
        diary_layout=diary_layout,
        photo_view=photo_view,
        diary_id=diary_id
    )
