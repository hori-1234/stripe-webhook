from flask import Blueprint

syuwa_bp = Blueprint(
    "syuwa",
    __name__,
    url_prefix="/syuwa"
)


@syuwa_bp.route("/apply", methods=["GET"])
def syuwa_apply():
    return "手話アプリ 登録者申請ページ"
