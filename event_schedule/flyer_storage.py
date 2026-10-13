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
