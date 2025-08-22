from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import VinRecord
from ..extensions import db
from ..security import role_required
from ..audit import log_action
from . import bp

# app/vin/routes.py
# @bp.route("/") for list_vins
# @bp.route("/create") for create_vin

@bp.route("/", methods=["GET"])
@login_required
def list_vins():
    q = request.args.get("q")
    items = VinRecord.query.filter(VinRecord.vin.contains(q)).all() if q else []
    log_action("vin_search", {"query":q})
    return render_template("vin/list.html", items=items, query=q)

@bp.route("/create", methods=["GET","POST"])
@login_required
@role_required("verifier","admin")
def create_vin():
    if request.method=="POST":
        vin = request.form.get("vin")
        meta = request.form.get("meta")
        record = VinRecord(vin=vin, meta={"info":meta}, created_by=current_user.id)
        db.session.add(record)
        db.session.commit()
        log_action("vin_create", {"vin":vin})
        flash("VIN record created.","success")
        return redirect(url_for("vin.list_vins"))
    return render_template("vin/create.html")