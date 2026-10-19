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

        <p>
            <button type="submit">変更を保存</button>
        </p>
    </form>

    <p>
        <a href="/oshikatsu/view/{{ diary_id }}">
            キャンセル
        </a>
    </p>
</body>
</html>
    """,
        diary_layout=diary_layout,
        photo_form=photo_form,
        diary_id=diary_id,
        csrf_token=csrf_token
    )
