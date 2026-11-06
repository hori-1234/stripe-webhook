import io
import os
import uuid
import boto3

from PIL import Image, ImageOps, UnidentifiedImageError
from botocore.config import Config
from flask import Blueprint, send_from_directory, request, current_app
from pathlib import Path

a_sya_bp = Blueprint(
    "a_sya",
    __name__,
    url_prefix="/a-sya"
)

ARTIST_DIR = Path(__file__).resolve().parent


@a_sya_bp.route("/", methods=["GET", "POST"])
def a_sya_submit():

    if request.method == "GET":
        return send_from_directory(
            str(ARTIST_DIR),
            "a-sya_submit.html"
        )

    # 画像を取得
    uploaded_file = request.files.get("image")

    if not uploaded_file or not uploaded_file.filename:
        return "画像を選択してください", 400

    # 活動情報を取得
    artist_name = request.form.get("artist_name", "").strip()
    artist_type = request.form.get("artist_type", "solo")

    if not artist_name:
        return "活動名を入力してください", 400

    if artist_type not in ("solo", "group"):
        return "活動形態が不正です", 400

    if artist_type == "group":
        member_names = request.form.getlist("member_name[]")
        member_colors = request.form.getlist("member_color[]")

        if (
            not member_names
            or len(member_names) != len(member_colors)
            or any(not name.strip() for name in member_names)
            or any(not color.strip() for color in member_colors)
        ):
            return "メンバー名とカラーを入力してください", 400

    else:
        image_color = request.form.get("image_color", "").strip()

        if not image_color:
            return "イメージカラーを入力してください", 400

    # R2へ画像保存
    try:
        file_key = save_artist_image(uploaded_file)
    except ValueError:
        return "画像ファイルを確認してください", 400
    except Exception:
        current_app.logger.exception("アー写のR2保存に失敗")
        return "画像の保存に失敗しました", 500

    return f"画像の保存が完了しました：{file_key}", 200


def save_artist_image(uploaded_file):
    # 画像を読み込む
    try:
        uploaded_file.stream.seek(0)

        with Image.open(uploaded_file.stream) as original:
            # EXIFの回転情報を反映
            img = ImageOps.exif_transpose(original)

            # 縦横の短い方を取得
            short_side = min(img.width, img.height)

            # 短辺が420pxを超える場合だけ縮小
            if short_side > 420:
                ratio = 420 / short_side

                new_width = round(img.width * ratio)
                new_height = round(img.height * ratio)

                img = img.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )

            # WebPで保存するためRGB/RGBAに変換
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

            output = io.BytesIO()
            img.save(output, format="WEBP", quality=85)
            output.seek(0)

    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ValueError("画像ファイルを読み込めません") from e

    # 保存するファイル名を自動生成
    file_key = f"{uuid.uuid4().hex}.webp"

    # アー写専用R2に接続
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["ARTIST_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["ARTIST_R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4")
    )

    # Cloudflare R2に保存
    client.put_object(
        Bucket=os.environ["ARTIST_R2_BUCKET_NAME"],
        Key=file_key,
        Body=output.getvalue(),
        ContentType="image/webp"
    )

    return file_key
