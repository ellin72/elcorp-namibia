from flask import Blueprint

bp = Blueprint(
    "vin",
    __name__,
    url_prefix="/vin",
    template_folder="templates/vin"    # points to app/vin/templates/vin/
)

from . import routes