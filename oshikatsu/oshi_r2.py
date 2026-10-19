import os
import boto3
from botocore.config import Config


def get_oshi_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["OSHI_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["OSHI_R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4")
    )


def get_oshi_r2_bucket():
    return os.environ["OSHI_R2_BUCKET_NAME"]
    

def test_oshi_r2_connection():
    client = get_oshi_r2_client()
    bucket = get_oshi_r2_bucket()

    client.head_bucket(Bucket=bucket)

    return True


def upload_oshi_photo(image_bytes, user_id, diary_id, photo_order):
    import uuid
    from oshikatsu.oshi_image import compress_oshi_image

    if not 1 <= photo_order <= 10:
        raise ValueError("写真の番号は1～10で指定してください")

    compressed_bytes = compress_oshi_image(image_bytes)

    r2_key = (
        f"diaries/{user_id}/{diary_id}/"
        f"{uuid.uuid4().hex}.webp"
    )

    client = get_oshi_r2_client()
    client.put_object(
        Bucket=get_oshi_r2_bucket(),
        Key=r2_key,
        Body=compressed_bytes,
        ContentType="image/webp"
    )

    return r2_key


def delete_oshi_photo(r2_key):
    if not r2_key or not r2_key.startswith("diaries/"):
        raise ValueError("不正な写真の保存先です")

    client = get_oshi_r2_client()

    client.delete_object(
        Bucket=get_oshi_r2_bucket(),
        Key=r2_key
    )


def get_oshi_photo(r2_key):
    if not r2_key or not r2_key.startswith("diaries/"):
        raise ValueError("不正な写真の保存先です")

    client = get_oshi_r2_client()

    response = client.get_object(
        Bucket=get_oshi_r2_bucket(),
        Key=r2_key
    )

    try:
        return response["Body"].read()
    finally:
        response["Body"].close()


def list_oshi_r2_photos():
    """
    R2の推し活日記画像をすべて取得する。
    画像本体は取得せず、キーと最終更新日時のみ返す。
    """

    client = get_oshi_r2_client()

    paginator = client.get_paginator("list_objects_v2")

    for page in paginator.paginate(
        Bucket=get_oshi_r2_bucket(),
        Prefix="diaries/"
    ):
        for obj in page.get("Contents", []):
            yield {
                "r2_key": obj["Key"],
                "last_modified": obj["LastModified"]
            }

def list_orphan_oshi_photos(min_age_hours=24):
    """
    PostgreSQLに登録されていないR2画像を抽出する。
    指定時間より新しい画像は対象外。
    この関数では削除しない。
    """

    import psycopg2
    from datetime import datetime, timedelta, timezone

    if min_age_hours < 24:
        raise ValueError("孤立画像の判定は24時間以上にしてください")

    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=min_age_hours
    )

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r2_key
                FROM oshi_diary_photos
            """)

            registered_keys = {
                row[0] for row in cur.fetchall()
            }

            cur.execute("""
                SELECT r2_key
                FROM oshi_photo_delete_queue
            """)

            queued_keys = {
                row[0] for row in cur.fetchall()
            }

    finally:
        conn.close()

    for photo in list_oshi_r2_photos():
        r2_key = photo["r2_key"]
        last_modified = photo["last_modified"]

        if last_modified > cutoff:
            continue

        if r2_key in registered_keys:
            continue

        if r2_key in queued_keys:
            continue

        yield r2_key


def delete_orphan_oshi_photos(min_age_hours=24):
    """
    24時間以上経過した孤立画像を削除する。
    削除直前にPostgreSQLの登録状況を再確認する。
    """

    import logging
    import psycopg2

    if min_age_hours < 24:
        raise ValueError("孤立画像の削除は24時間以上にしてください")

    deleted_count = 0

    for r2_key in list_orphan_oshi_photos(min_age_hours):
        conn = psycopg2.connect(os.environ["DATABASE_URL"])

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM oshi_diary_photos
                        WHERE r2_key = %s
                    ) OR EXISTS (
                        SELECT 1
                        FROM oshi_photo_delete_queue
                        WHERE r2_key = %s
                    )
                """, (r2_key, r2_key))

                is_registered = cur.fetchone()[0]

            if is_registered:
                continue

            try:
                delete_oshi_photo(r2_key)
                deleted_count += 1
            except Exception:
                logging.exception(
                    "孤立画像のR2削除に失敗しました: %s",
                    r2_key
                )

        finally:
            conn.close()

    return deleted_count
