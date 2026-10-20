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
        .nikki-demo-button {
            min-width: 150px;
            min-height: 48px;
            padding: 10px 24px;
            font-size: 18px;
            font-weight: bold;
            border: 1px solid #888;
            border-radius: 6px;
            background: #f5f5f5;
            color: #000;
            cursor: pointer;
        }

        .nikki-demo-button:hover {
            background: #e5e5e5;
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
