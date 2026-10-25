from flask import Blueprint, render_template

syuwa_bp = Blueprint(
    "syuwa",
    __name__,
    url_prefix="/syuwa",
    template_folder="templates"
)


@syuwa_bp.route("/apply", methods=["GET"])
def syuwa_apply():
    return render_template("syuwa_apply.html")
