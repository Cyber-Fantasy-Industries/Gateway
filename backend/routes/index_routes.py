from flask import Blueprint, render_template
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "web_dashboard", "templates"))

index_bp = Blueprint(
    "index",
    __name__,
    template_folder=TEMPLATES_DIR
)

@index_bp.route("/")
def index():
    return render_template("base.html")
