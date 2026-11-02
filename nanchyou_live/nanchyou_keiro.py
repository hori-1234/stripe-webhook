from flask import Blueprint, render_template

nanchyou_bp = Blueprint(
    "nanchyou",
    __name__,
    template_folder="templates"
)

@nanchyou_bp.route("/nanchyou_live")
def nanchyou_live():
    return render_template("index.html")
