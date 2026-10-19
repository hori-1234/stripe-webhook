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
