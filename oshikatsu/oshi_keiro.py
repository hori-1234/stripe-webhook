from flask import Blueprint

oshikatsu_bp = Blueprint(
    "oshikatsu",
    __name__,
    url_prefix="/oshikatsu"
)
