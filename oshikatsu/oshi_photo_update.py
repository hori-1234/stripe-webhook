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
