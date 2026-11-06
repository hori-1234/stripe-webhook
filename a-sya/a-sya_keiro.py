import io
import os
import uuid
import boto3
import psycopg2

from botocore.exceptions import ClientError
from flask import send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from botocore.config import Config
from flask import Blueprint, send_from_directory, request, current_app, jsonify
from pathlib import Path
from admin_auth import admin_required
import importlib.util

artist_db_path = Path(__file__).resolve().parent / "a-sya_db.py"
artist_db_spec = importlib.util.spec_from_file_location(
    "a_sya_db",
    artist_db_path
)
artist_db_module = importlib.util.module_from_spec(artist_db_spec)
artist_db_spec.loader.exec_module(artist_db_module)

save_artist_submission = artist_db_module.save_artist_submission
get_artist_submissions = artist_db_module.get_artist_submissions
delete_artist_submission = artist_db_module.delete_artist_submission

a_sya_bp = Blueprint(
    "a_sya",
    __name__,
    url_prefix="/a-sya"
)

ARTIST_DIR = Path(__file__).resolve().parent


@a_sya_bp.route("/admin/", methods=["GET"])
@admin_required
def a_sya_admin():
    return send_from_directory(
        str(ARTIST_DIR),
        "a-sya_admin.html"
    )


@a_sya_bp.route("/admin/list", methods=["GET"])
@admin_required
def a_sya_admin_list():
    try:
        submissions = get_artist_submissions()

        for submission in submissions:
            submission.pop("image_key", None)

        return jsonify({
            "count": len(submissions),
            "submissions": submissions
        })

    except Exception:
        current_app.logger.exception("アー写一覧取得に失敗")
        return jsonify({
            "error": "一覧の取得に失敗しました"
        }), 500


@a_sya_bp.route("/admin/image/<int:submission_id>", methods=["GET"])
@admin_required
def a_sya_admin_image(submission_id):
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT image_key
                    FROM artist_submissions
                    WHERE id = %s
                """, (submission_id,))
                row = cur.fetchone()
        finally:
            conn.close()

        if row is None:
            return "画像が見つかりません", 404

        client = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["ARTIST_R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["ARTIST_R2_SECRET_ACCESS_KEY"],
            region_name="auto",
            config=Config(signature_version="s3v4")
        )

        result = client.get_object(
            Bucket=os.environ["ARTIST_R2_BUCKET_NAME"],
            Key=row[0]
        )

        image_data = result["Body"].read()

        return send_file(
            io.BytesIO(image_data),
            mimetype="image/webp"
        )
    
    except Exception:
        current_app.logger.exception("アー写の画像取得に失敗")
        return "画像の取得に失敗しました", 500


@a_sya_bp.route("/admin/download/<int:submission_id>", methods=["GET"])
@admin_required
def a_sya_admin_download(submission_id):
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT image_key, artist_name
                    FROM artist_submissions
                    WHERE id = %s
                """, (submission_id,))
                row = cur.fetchone()
        finally:
            conn.close()

        if row is None:
            return "画像が見つかりません", 404

        client = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["ARTIST_R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["ARTIST_R2_SECRET_ACCESS_KEY"],
            region_name="auto",
            config=Config(signature_version="s3v4")
        )

        result = client.get_object(
            Bucket=os.environ["ARTIST_R2_BUCKET_NAME"],
            Key=row[0]
        )

        # R2のWebP画像を読み込む
        image_data = result["Body"].read()

        with Image.open(io.BytesIO(image_data)) as img:
            # JPEGは透過非対応なので白背景に変換
            img = img.convert("RGBA")

            background = Image.new(
                "RGB",
                img.size,
                (255, 255, 255)
            )

            background.paste(img, mask=img.getchannel("A"))

            # JPEG形式に変換
            output = io.BytesIO()
            background.save(
                output,
                format="JPEG",
                quality=90
            )
            output.seek(0)
        
        safe_name = "".join(
            "_" if c in '/\\:*?"<>|\r\n' or ord(c) < 32 else c
            for c in row[1]
        ).strip().strip(".")

        if not safe_name:
            safe_name = f"artist_{submission_id}"

        return send_file(
            output,
            mimetype="image/jpeg",
            as_attachment=True,
            download_name=f"{safe_name}.jpg"
        )

    except Exception:
        current_app.logger.exception("アー写のダウンロードに失敗")
        return "ダウンロードに失敗しました", 500



@a_sya_bp.route("/admin/delete/<int:submission_id>", methods=["POST"])
@admin_required
def a_sya_admin_delete(submission_id):

    def delete_r2_image(image_key):
        client = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["ARTIST_R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["ARTIST_R2_SECRET_ACCESS_KEY"],
            region_name="auto",
            config=Config(signature_version="s3v4")
        )

        client.delete_object(
            Bucket=os.environ["ARTIST_R2_BUCKET_NAME"],
            Key=image_key
        )

    try:
        deleted = delete_artist_submission(
            submission_id,
            delete_r2_image
        )

        if not deleted:
            return jsonify({
                "error": "対象データが見つかりません"
            }), 404

        return jsonify({
            "success": True,
            "message": "削除しました"
        })

    except Exception:
        current_app.logger.exception("アー写の削除に失敗")
        return jsonify({
            "error": "削除に失敗しました"
        }), 500


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

    
    # DB保存用の情報を整理
    members = []

    if artist_type == "group":
        for name, color in zip(member_names, member_colors):
            members.append({
                "name": name.strip(),
                "color": color.strip()
            })

        image_color = None

    # PostgreSQLに保存
    try:
        submission_id = save_artist_submission(
            artist_name=artist_name,
            artist_type=artist_type,
            image_color=image_color,
            image_key=file_key,
            members=members
        )

    except Exception:
        current_app.logger.exception("アー写のDB保存に失敗")

        # DB保存失敗時はR2に保存した画像も削除
        try:
            client = boto3.client(
                "s3",
                endpoint_url=os.environ["R2_ENDPOINT"],
                aws_access_key_id=os.environ["ARTIST_R2_ACCESS_KEY_ID"],
                aws_secret_access_key=os.environ["ARTIST_R2_SECRET_ACCESS_KEY"],
                region_name="auto",
                config=Config(signature_version="s3v4")
            )

            client.delete_object(
                Bucket=os.environ["ARTIST_R2_BUCKET_NAME"],
                Key=file_key
            )

        except Exception:
            current_app.logger.exception("アー写のR2後処理に失敗")

        return "登録情報の保存に失敗しました", 500

    return f"アー写の提出が完了しました（受付番号：{submission_id}）", 200


    
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
