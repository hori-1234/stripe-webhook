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
