import os
import boto3
from botocore.config import Config


# イベスケのフライヤー専用R2接続
FLYER_BUCKET = os.environ["IBESUKE_R2_BUCKET"]


def get_flyer_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["IBESUKE_R2_ENDPOINT"],
        aws_access_key_id=os.environ["IBESUKE_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["IBESUKE_R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4")
    )


from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError


def convert_flyer_to_webp(uploaded_file):
    # アップロード上限：2MB
    max_file_size = 2 * 1024 * 1024

    image_data = uploaded_file.stream.read(max_file_size + 1)

    if len(image_data) > max_file_size:
        raise ValueError("画像サイズは2MB以内にしてください。")

    if not image_data:
        raise ValueError("画像ファイルを選択してください。")

    # ファイルの実際の形式を確認
    try:
        with Image.open(BytesIO(image_data)) as image:
            if image.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError("JPG・PNG・WebP形式のみ登録できます。")

            if image.width * image.height > 20_000_000:
                raise ValueError("画像の画素数が大きすぎます。")

            # スマホ写真の回転情報を反映
            image = ImageOps.exif_transpose(image)

            # 透明部分がある画像にも対応
            image = image.convert("RGBA")

            results = {}

            for name, max_edge in (
                ("thumbnail", 300),
                ("image", 1200)
            ):
                resized = image.copy()
                resized.thumbnail(
                    (max_edge, max_edge),
                    Image.Resampling.LANCZOS
                )

                output = BytesIO()
                resized.save(
                    output,
                    format="WEBP",
                    quality=80,
                    method=6
                )

                results[name] = output.getvalue()

            return results

    except (UnidentifiedImageError, OSError):
        raise ValueError("画像ファイルを読み込めませんでした。")

import secrets


def upload_flyer_to_r2(uploaded_file):
    # 画像をWebP形式に変換
    images = convert_flyer_to_webp(uploaded_file)

    # 推測されにくいランダムなファイル名を生成
    image_id = secrets.token_hex(16)

    thumbnail_key = f"flyers/{image_id}_thumbnail.webp"
    image_key = f"flyers/{image_id}_image.webp"

    r2 = get_flyer_r2_client()

    uploaded_keys = []

    try:
        # サムネイル画像を保存
        r2.put_object(
            Bucket=FLYER_BUCKET,
            Key=thumbnail_key,
            Body=images["thumbnail"],
            ContentType="image/webp"
        )

        uploaded_keys.append(thumbnail_key)

        # 拡大表示用画像を保存
        r2.put_object(
            Bucket=FLYER_BUCKET,
            Key=image_key,
            Body=images["image"],
            ContentType="image/webp"
        )

        uploaded_keys.append(image_key)

    except Exception:
        # 途中で失敗した場合、保存済みの画像を削除
        for key in uploaded_keys:
            try:
                r2.delete_object(
                    Bucket=FLYER_BUCKET,
                    Key=key
                )
            except Exception:
                pass

        raise

    return thumbnail_key, image_key


def delete_flyer_from_r2(thumbnail_key, image_key):
    r2 = get_flyer_r2_client()

    keys = [
        key for key in (thumbnail_key, image_key)
        if key
    ]

    if not keys:
        return

    # 画像を1件ずつ削除
    for key in keys:
        r2.delete_object(
            Bucket=FLYER_BUCKET,
            Key=key
        )


def get_flyer_url(image_key):
    if not image_key:
        return None

    r2 = get_flyer_r2_client()

    return r2.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": FLYER_BUCKET,
            "Key": image_key
        },
        ExpiresIn=3600
    )
