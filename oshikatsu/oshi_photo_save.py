from oshikatsu.oshi_r2 import (
    upload_oshi_photo,
    delete_oshi_photo
)


def save_oshi_photos(conn, photos, user_id, diary_id):
    """
    日記の写真をR2に保存し、
    oshi_diary_photosテーブルに登録する。
    """

    valid_photos = [
        photo
        for photo in photos
        if photo and photo.filename
    ]

    if len(valid_photos) > 10:
        raise ValueError("写真は最大10枚までです")

    uploaded_keys = []

    try:
        with conn.cursor() as cur:
            for photo_order, photo in enumerate(
                valid_photos,
                start=1
            ):
                if not photo.mimetype.startswith("image/"):
                    raise ValueError(
                        "画像ファイル以外は登録できません"
                    )

                image_bytes = photo.read()

                if not image_bytes:
                    raise ValueError(
                        "空の画像ファイルは登録できません"
                    )

                if len(image_bytes) > 20 * 1024 * 1024:
                    raise ValueError(
                        "画像は1枚20MB以下にしてください"
                    )

                r2_key = upload_oshi_photo(
                    image_bytes=image_bytes,
                    user_id=str(user_id),
                    diary_id=diary_id,
                    photo_order=photo_order
                )

                uploaded_keys.append(r2_key)

                cur.execute("""
                    INSERT INTO oshi_diary_photos (
                        diary_id,
                        r2_key,
                        photo_order
                    )
                    VALUES (%s, %s, %s)
                """, (
                    diary_id,
                    r2_key,
                    photo_order
                ))

    except Exception:
        for r2_key in uploaded_keys:
            try:
                delete_oshi_photo(r2_key)
            except Exception:
                # R2削除失敗時はログに記録する
                import logging
                logging.exception(
                    "写真の後片付けに失敗しました: %s",
                    r2_key
                )

        raise

    return len(valid_photos)
