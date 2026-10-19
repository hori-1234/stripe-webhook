from flask import Blueprint
from oshikatsu.oshi_r2 import test_oshi_r2_connection

try:
    test_oshi_r2_connection()
    print("推し活日記R2接続成功", flush=True)
except Exception as e:
    print(f"推し活日記R2接続失敗: {type(e).__name__}", flush=True)

oshikatsu_bp = Blueprint(
    "oshikatsu",
    __name__,
    url_prefix="/oshikatsu"
)
