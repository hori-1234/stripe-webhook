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
