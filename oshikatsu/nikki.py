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

    <style>
        .login-button {
            display: inline-block;
            padding: 6px 12px;
            border: 1px solid #888;
            background: #f5f5f5;
            color: #000;
            text-decoration: none;
            font-size: 13px;
        }

        .login-button:hover {
            background: #e5e5e5;
        }
    </style>
</head>

<body>
    <h2>推し活日記</h2>

    {% if logged_in %}
        <p>ログイン中</p>
    {% else %}
        <p>未ログイン：入力内容は保存できません。</p>
         <a href="/schedule/login" class="login-button">新規登録・ログイン</a>
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


def render_nikki_view(
    diary,
    photo_view="",
    diary_id=None,
    prev_diary_id=None,
    next_diary_id=None
):    
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

    <style>
        .nikki-view-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            max-width: 700px;
            gap: 12px;
        }

        .nikki-view-header h2 {
            margin: 16px 0;
            text-align: center;
        }

        .nikki-move-button,
        .nikki-move-empty {
            width: 50px;
            height: 60px;
            flex-shrink: 0;
        }

        .nikki-move-button {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            color: #222;
            background: rgba(128, 128, 128, 0.15);
            border-radius: 6px;
            text-decoration: none;
        }

        .nikki-move-button:hover {
            background: rgba(128, 128, 128, 0.3);
        }

                .nikki-page-loading {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 100000;
            background: rgba(0, 0, 0, 0.65);
            align-items: center;
            justify-content: center;
        }

        .nikki-page-loading.is-loading {
            display: flex;
        }

        .nikki-page-loading-spinner {
            width: 52px;
            height: 52px;
            border: 6px solid rgba(255, 255, 255, 0.25);
            border-top: 6px solid #ffffff;
            border-radius: 50%;
            animation: nikki-page-spin 0.8s linear infinite;
        }

        @keyframes nikki-page-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    </style>
</head>

<body>
    <div class="nikki-view-header">
        {% if prev_diary_id is not none %}
            <a href="/oshikatsu/view/{{ prev_diary_id }}"
               class="nikki-move-button"
               aria-label="前の日記">＜</a>
        {% else %}
            <span class="nikki-move-empty"></span>
        {% endif %}

        <h2>推し活日記</h2>

        {% if next_diary_id is not none %}
            <a href="/oshikatsu/view/{{ next_diary_id }}"
               class="nikki-move-button"
               aria-label="次の日記">＞</a>
        {% else %}
            <span class="nikki-move-empty"></span>
        {% endif %}
    </div>

    {{ diary_layout }}

    {{ photo_view }}

    <p>
        <a href="/oshikatsu/edit/{{ diary_id }}">編集</a>
    </p>
    
    <p><a href="/schedule">イベスケへ戻る</a></p>

    <div class="nikki-page-loading" id="nikki-page-loading">
        <div class="nikki-page-loading-spinner"></div>
    </div>

    <script>
        document.querySelectorAll(".nikki-move-button").forEach(function (button) {
            button.addEventListener("click", function () {
                document.getElementById("nikki-page-loading")
                    .classList.add("is-loading");
            });
        });

        window.addEventListener("pageshow", function () {
            document.getElementById("nikki-page-loading")
                .classList.remove("is-loading");
        });
    </script>
</body>
</html>
    """,
        diary_layout=diary_layout,
        photo_view=photo_view,
        diary_id=diary_id,
        prev_diary_id=prev_diary_id,
        next_diary_id=next_diary_id                          
    )
