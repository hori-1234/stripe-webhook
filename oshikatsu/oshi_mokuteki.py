from flask import Blueprint, render_template

oshi_mokuteki_bp = Blueprint(
    "oshi_mokuteki",
    __name__,
    url_prefix="/oshikatsu"
)


@oshi_mokuteki_bp.route("/purpose")
def oshi_mokuteki():
    return render_template("oshikatsu_purpose.html")
