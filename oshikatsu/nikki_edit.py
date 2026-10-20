from flask import render_template_string

from oshikatsu.nikki_layout import render_nikki_layout
from oshikatsu.nikki_photo import render_nikki_photo_form


def render_nikki_edit(diary, diary_id, csrf_token, saved_photos=None):

    diary_layout = render_nikki_layout(
        diary=diary,
        mode="edit"
    )

    photo_form = render_nikki_photo_form(
        saved_photos=saved_photos
    )

    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">
    <title>推し活日記 - 編集</title>

    <style>
        /* 手帳風の背景 */
        body {
            margin: 0;
            padding: 30px 15px 60px;
            background: #f5f0e6;
            color: #493c30;
            font-family: sans-serif;
            line-height: 1.7;
        }

        /* 日記の用紙 */
        body > h2,
        body > form {
            max-width: 760px;
            margin-left: auto;
            margin-right: auto;
            box-sizing: border-box;
        }

        body > h2 {
            margin-top: 0;
            margin-bottom: 0;
            padding: 28px 30px 15px;
            background: #fffdf8;
            border: 1px solid #e2d4bf;
            border-bottom: none;
            border-radius: 12px 12px 0 0;
            color: #725334;
            font-size: 24px;
        }

        body > form {
            padding: 15px 30px 35px;
            background: #fffdf8;
            border: 1px solid #e2d4bf;
            border-top: none;
            border-radius: 0 0 12px 12px;
            box-shadow: 0 8px 24px rgba(94, 72, 44, 0.10);
        }

        /* 入力欄 */
        input[type="text"],
        input[type="date"],
        input[type="datetime-local"],
        textarea,
        select {
            max-width: 100%;
            box-sizing: border-box;
            background: #fffefa;
            color: #493c30;
            border: 1px solid #d8c8b2;
            border-radius: 5px;
            padding: 9px;
            font-size: 16px;
        }

        textarea {
            line-height: 1.9;
            background-image: none;
        }

        input:focus,
        textarea:focus,
        select:focus {
            outline: 2px solid #c8a77c;
            outline-offset: 1px;
        }

        /* 写真 */
        img {
            max-width: 100%;
            height: auto;
        }

        /* 保存・戻るボタン */
        .nikki-demo-button {
            min-width: 120px;
            min-height: 48px;
            padding: 10px 20px;
            font-size: 16px;
            font-weight: bold;
            border: 1px solid #bca789;
            border-radius: 6px;
            background: #eee2d0;
            color: #493c30;
            cursor: pointer;
        }

        .nikki-demo-button:hover {
            background: #e3d1b7;
        }

        @media (max-width: 600px) {
            body {
                padding: 15px 10px 40px;
            }

            body > h2 {
                padding: 20px 16px 12px;
                font-size: 21px;
            }

            body > form {
                padding: 12px 16px 25px;
            }

            .nikki-demo-button {
                min-width: 100px;
                padding: 10px 15px;
                font-size: 15px;
            }
        }
    </style>

</head>
<body>
    <h2>推し活日記 - 編集</h2>

    <form
        method="POST"
        action="/oshikatsu/update/{{ diary_id }}"
        enctype="multipart/form-data"
    >
        <input
            type="hidden"
            name="csrf_token"
            value="{{ csrf_token }}"
        >

        {{ diary_layout }}

        {{ photo_form }}

        <p style="display: flex; align-items: center; gap: 12px;">
            <button type="submit" class="nikki-demo-button">保存</button>

            <a href="/oshikatsu/view/{{ diary_id }}"
               class="nikki-demo-button"
               style="display: inline-flex; align-items: center; justify-content: center; box-sizing: border-box; text-decoration: none;">
                戻る
            </a>
        </p>
    </form>

</body>
</html>
    """,
        diary_layout=diary_layout,
        photo_form=photo_form,
        diary_id=diary_id,
        csrf_token=csrf_token
    )
