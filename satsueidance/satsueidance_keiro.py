
from flask import Blueprint, render_template

satsueidance_bp = Blueprint(
    "satsueidance",
    __name__,
    template_folder="templates",
    url_prefix="/satsueidance"
)


@satsueidance_bp.route("/")
def satsueidance_index():
    return render_template("index.html")
