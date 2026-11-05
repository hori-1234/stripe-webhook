from flask import Blueprint

a_sya_bp = Blueprint(
    "a_sya",
    __name__,
    url_prefix="/a-sya"
)


@a_sya_bp.route("/", methods=["GET"])
def a_sya_submit():
    return "アー写投稿ページ"
