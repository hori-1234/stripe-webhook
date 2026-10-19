import json


def validate_oshi_photo_update(form, photos):
    """
    写真更新リクエストの基本検証。
    戻り値: (表示順データ, 削除対象ID, 新規写真)
    """

    try:
        order_data = json.loads(
            form.get("photo_order_data", "[]")
        )
    except (TypeError, ValueError):
        raise ValueError("写真の並び順データが不正です")

    if not isinstance(order_data, list):
        raise ValueError("写真の並び順データが不正です")

    valid_photos = [
        photo for photo in photos
        if photo and photo.filename
    ]

    if len(valid_photos) > 10:
        raise ValueError("写真は最大10枚までです")

    if len(order_data) > 10:
        raise ValueError("写真は最大10枚までです")

    removed_ids = []

    for value in form.getlist("remove_photo_ids"):
        try:
            photo_id = int(value)
        except (TypeError, ValueError):
            raise ValueError("削除する写真IDが不正です")

        if photo_id <= 0:
            raise ValueError("削除する写真IDが不正です")

        removed_ids.append(photo_id)

    if len(removed_ids) != len(set(removed_ids)):
        raise ValueError("削除する写真IDが重複しています")

    for index, item in enumerate(order_data, start=1):
        if not isinstance(item, dict):
            raise ValueError("写真の並び順データが不正です")

        if item.get("photo_order") != index:
            raise ValueError("写真の並び順が不正です")

        photo_id = item.get("photo_id")
        new_index = item.get("new_photo_index")

        if (photo_id is None) == (new_index is None):
            raise ValueError("写真の識別情報が不正です")

        if photo_id is not None:
            if (
                not isinstance(photo_id, (str, int))
                or not str(photo_id).isdigit()
                or int(photo_id) <= 0
            ):
                raise ValueError("写真IDが不正です")

        if new_index is not None:
            if (
                type(new_index) is not int
                or not 0 <= new_index < len(valid_photos)
            ):
                raise ValueError("新規写真の番号が不正です")

    return order_data, removed_ids, valid_photos


def get_oshi_photo_update_targets(
    conn,
    diary_id,
    user_id
):
    """
    日記の所有者を確認し、
    保存済み写真のID・R2キー・表示順を取得する。
    """

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id
            FROM oshi_diaries
            WHERE id = %s
              AND user_id = %s
            FOR UPDATE
        """, (
            diary_id,
            str(user_id)
        ))

        if cur.fetchone() is None:
            raise ValueError("日記が見つかりません")

        cur.execute("""
            SELECT
                id,
                r2_key,
                photo_order
            FROM oshi_diary_photos
            WHERE diary_id = %s
            ORDER BY photo_order, id
            FOR UPDATE
        """, (diary_id,))

        rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "r2_key": row[1],
            "photo_order": row[2]
        }
        for row in rows
    ]

def check_oshi_photo_update_targets(
    saved_photos,
    order_data,
    removed_ids,
    new_photos
):
    """
    保存済み写真と送信内容の整合性を確認する。
    """

    saved_ids = {
        photo["id"]
        for photo in saved_photos
    }

    removed_set = set(removed_ids)

    if not removed_set.issubset(saved_ids):
        raise ValueError("削除対象に不正な写真IDがあります")

    ordered_saved_ids = []
    ordered_new_indices = []

    for item in order_data:
        photo_id = item["photo_id"]
        new_index = item["new_photo_index"]

        if photo_id is not None:
            ordered_saved_ids.append(int(photo_id))
        else:
            ordered_new_indices.append(new_index)

    if len(ordered_saved_ids) != len(set(ordered_saved_ids)):
        raise ValueError("同じ写真が重複指定されています")

    if len(ordered_new_indices) != len(set(ordered_new_indices)):
        raise ValueError("新規写真が重複指定されています")

    remaining_ids = saved_ids - removed_set

    if set(ordered_saved_ids) != remaining_ids:
        raise ValueError("保存済み写真の指定が一致しません")

    if set(ordered_new_indices) != set(range(len(new_photos))):
        raise ValueError("新規写真の指定が一致しません")

    if len(order_data) != len(remaining_ids) + len(new_photos):
        raise ValueError("写真の枚数が一致しません")

    if len(order_data) > 10:
        raise ValueError("写真は最大10枚までです")

    return True


def insert_oshi_updated_photos(
    conn,
    diary_id,
    user_id,
    new_photos,
    order_data
):
    """
    新規写真をR2へアップロードし、
    PostgreSQLへ登録する。

    呼び出し元で写真ID・枚数・表示順の検証と
    トランザクション管理を行う。
    """

    from oshikatsu.oshi_r2 import (
        upload_oshi_photo,
        delete_oshi_photo
    )

    uploaded_keys = []

    try:
        with conn.cursor() as cur:
            for item in order_data:
                new_index = item["new_photo_index"]

                if new_index is None:
                    continue

                photo = new_photos[new_index]

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

                photo_order = item["photo_order"]

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
                import logging
                logging.exception(
                    "写真更新時のR2後片付けに失敗しました: %s",
                    r2_key
                )

        raise

    return len(uploaded_keys)


def delete_oshi_updated_photos(
    conn,
    saved_photos,
    removed_ids
):
    """
    削除指定された写真をR2から削除し、
    成功した写真だけPostgreSQLから削除する。

    呼び出し元で所有者確認と
    トランザクション管理を行う。
    """

    from oshikatsu.oshi_r2 import delete_oshi_photo

    removed_set = set(removed_ids)

    delete_targets = [
        photo
        for photo in saved_photos
        if photo["id"] in removed_set
    ]

    with conn.cursor() as cur:
        for photo in delete_targets:
            # R2側の削除を先に実行する
            delete_oshi_photo(photo["r2_key"])

            # R2削除成功後にDB側の情報を削除する
            cur.execute("""
                DELETE FROM oshi_diary_photos
                WHERE id = %s
                  AND r2_key = %s
            """, (
                photo["id"],
                photo["r2_key"]
            ))

            if cur.rowcount != 1:
                raise RuntimeError(
                    "写真のDB削除に失敗しました"
                )

    return len(delete_targets)

